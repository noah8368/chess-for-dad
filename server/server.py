#!/usr/bin/env python3
"""Chess For Dad — live sync server.

Holds one shared game and keeps two devices in step. The OmegaZero rules brain
(the compiled `chess-for-dad` binary) is the single source of truth for move
legality and game status; this server never re-implements chess rules. Moves
are pushed to the other device over Server-Sent Events, so there are no
third-party dependencies to install — just Python 3 and the built binary.

Endpoints
    GET  /                 the game (static files from the repo root)
    GET  /api/state        current game state as JSON
    GET  /api/events       Server-Sent Events stream of state updates
    POST /api/move         {"move": "e2e4"}  -> apply a move (authoritative)
    POST /api/undo         take back the last move
    POST /api/new          start a new game (optional {"w":..,"b":..} names)
    POST /api/names        {"w": "Dad", "b": "Noah"}  set player names

Run
    python3 server/server.py            # serves on http://localhost:8000
    python3 server/server.py --port 9000 --bin ./chess-for-dad
"""

import argparse
import json
import os
import queue
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Repo root is the parent of this file's directory; static files live there.
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SERVER_DIR)


def position_key(fen):
    """Board + side + castling + en-passant (the fields that define a position
    for threefold repetition), ignoring the move clocks."""
    return " ".join(fen.split(" ")[:4])


def insufficient_material(fen):
    """True when neither side has enough material to checkmate: lone kings, or
    king vs king plus a single minor piece."""
    placement = fen.split(" ")[0]
    non_king = [c.upper() for c in placement
                if c.isalpha() and c.upper() != "K"]
    if len(non_king) == 0:
        return True
    if len(non_king) == 1 and non_king[0] in ("B", "N"):
        return True
    return False


class RulesBrain:
    """Thin wrapper over the compiled `chess-for-dad` binary."""

    def __init__(self, binary):
        self.binary = binary

    def apply(self, fen, move):
        """Return (new_fen, status) for a legal move, or (None, None) if the
        move is illegal."""
        result = subprocess.run(
            [self.binary, "apply", fen, move],
            capture_output=True,
            text=True,
            timeout=10,
        )
        new_fen = None
        status = None
        for line in result.stdout.splitlines():
            if line.startswith("fen: "):
                new_fen = line[len("fen: "):].strip()
            elif line.startswith("status: "):
                status = line[len("status: "):].strip()
        if new_fen is None or status is None:
            return None, None
        return new_fen, status


class Game:
    """The single shared game. All mutation goes through `lock`."""

    def __init__(self, brain):
        self.brain = brain
        self.lock = threading.Lock()
        self.subscribers = []
        self.names = {"w": "White", "b": "Black"}
        self.reset()

    # --- state ---------------------------------------------------------------

    def reset(self):
        self.fen = START_FEN
        self.last_move = None
        self.status = "ongoing"
        self.moves = []
        self.undo_stack = []
        self.position_counts = {position_key(START_FEN): 1}
        self.version = 0

    def snapshot(self):
        return {
            "fen": self.fen,
            "turn": "w" if self.fen.split(" ")[1] == "w" else "b",
            "lastMove": self.last_move,
            "status": self.status,
            "moves": list(self.moves),
            "names": dict(self.names),
            "canUndo": len(self.undo_stack) > 0,
            "version": self.version,
        }

    # --- pub/sub -------------------------------------------------------------

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def _broadcast_locked(self):
        self.version += 1
        snap = self.snapshot()
        for q in self.subscribers:
            q.put(snap)

    # --- actions -------------------------------------------------------------

    def make_move(self, move):
        """Apply a move. Returns (ok, snapshot_or_error)."""
        with self.lock:
            if self.status in ("checkmate", "draw"):
                return False, {"error": "game over"}
            new_fen, status = self.brain.apply(self.fen, move)
            if new_fen is None:
                return False, {"error": "illegal move"}
            self.undo_stack.append((self.fen, self.last_move, self.status,
                                    dict(self.position_counts)))
            self.fen = new_fen
            self.last_move = move
            self.moves.append(move)
            key = position_key(new_fen)
            self.position_counts[key] = self.position_counts.get(key, 0) + 1
            # The binary settles check/checkmate/stalemate/fifty-move from the
            # FEN; history- and material-based draws are decided here.
            if status != "checkmate" and (
                    self.position_counts[key] >= 3
                    or insufficient_material(new_fen)):
                status = "draw"
            self.status = status
            self._broadcast_locked()
            return True, self.snapshot()

    def undo(self):
        with self.lock:
            if not self.undo_stack:
                return False, {"error": "nothing to undo"}
            self.fen, self.last_move, self.status, self.position_counts = (
                self.undo_stack.pop())
            if self.moves:
                self.moves.pop()
            self._broadcast_locked()
            return True, self.snapshot()

    def new_game(self, names=None):
        with self.lock:
            self.reset()
            if names:
                self._apply_names_locked(names)
            self._broadcast_locked()
            return self.snapshot()

    def set_names(self, names):
        with self.lock:
            self._apply_names_locked(names)
            self._broadcast_locked()
            return self.snapshot()

    def _apply_names_locked(self, names):
        for side in ("w", "b"):
            value = names.get(side)
            if isinstance(value, str) and value.strip():
                self.names[side] = value.strip()[:16]


class Handler(BaseHTTPRequestHandler):
    game = None  # injected before serving

    # Quieter logging than the noisy default.
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            self._send_json(self.game.snapshot())
            return
        if path == "/api/events":
            self._serve_sse()
            return
        self._serve_static(path)

    def do_POST(self):
        path = self.path.split("?")[0]
        payload = self._read_json()
        if path == "/api/move":
            move = (payload or {}).get("move", "")
            ok, result = self.game.make_move(move)
            self._send_json(result, 200 if ok else 409)
            return
        if path == "/api/undo":
            ok, result = self.game.undo()
            self._send_json(result, 200 if ok else 409)
            return
        if path == "/api/new":
            self._send_json(self.game.new_game(payload or {}))
            return
        if path == "/api/names":
            self._send_json(self.game.set_names(payload or {}))
            return
        self._send_json({"error": "not found"}, 404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        q = self.game.subscribe()
        try:
            self._write_event(self.game.snapshot())
            while True:
                try:
                    snap = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                self._write_event(snap)
        except (BrokenPipeError, ConnectionResetError, ValueError):
            pass
        finally:
            self.game.unsubscribe(q)

    def _write_event(self, obj):
        self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode())
        self.wfile.flush()

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        # Resolve inside the repo root and refuse anything that escapes it.
        target = os.path.normpath(os.path.join(REPO_ROOT, path.lstrip("/")))
        if not target.startswith(REPO_ROOT) or not os.path.isfile(target):
            self._send_json({"error": "not found"}, 404)
            return
        ctype = {
            ".html": "text/html",
            ".mjs": "text/javascript",
            ".js": "text/javascript",
            ".css": "text/css",
            ".jpg": "image/jpeg",
            ".png": "image/png",
        }.get(os.path.splitext(target)[1], "application/octet-stream")
        with open(target, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Chess For Dad sync server")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="")
    parser.add_argument(
        "--bin",
        default=os.environ.get("CHESS_FOR_DAD_BIN",
                               os.path.join(REPO_ROOT, "chess-for-dad")),
        help="path to the compiled chess-for-dad rules-brain binary",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.bin):
        raise SystemExit(
            "Rules-brain binary not found at '%s'. Build it first with `make`."
            % args.bin)

    brain = RulesBrain(args.bin)
    Handler.game = Game(brain)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Chess For Dad server on http://localhost:%d  (rules brain: %s)"
          % (args.port, args.bin))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
