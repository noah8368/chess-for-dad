# Chess For Dad — sync server 🔌

A tiny, dependency-free Python server that lets two devices share one game live.
It holds the single game and asks the compiled **`chess-for-dad`** rules brain to
validate and apply every move — so legality and game status come from OmegaZero's
own move generator, never a second chess implementation.

## Run

The easy way, from the repo root:

```
./start.sh                # builds the rules brain if needed, then serves
```

Or manually:

```
make                      # build the rules brain (from the repo root)
python3 server/server.py  # serve on http://localhost:8000
```

Open `http://localhost:8000` on two devices on the same network (use the host's
LAN IP on the second device). Moves made on one appear on the other instantly.

Options: `--port 9000`, `--host 0.0.0.0`, `--bin ./chess-for-dad`
(or set `CHESS_FOR_DAD_BIN`).

## API

| Method | Path          | Body                     | Purpose                          |
|--------|---------------|--------------------------|----------------------------------|
| GET    | `/api/state`  | —                        | current game state (JSON)        |
| GET    | `/api/events` | —                        | Server-Sent Events state stream  |
| POST   | `/api/move`   | `{"move":"e2e4"}`        | apply a move (409 if illegal)    |
| POST   | `/api/undo`   | —                        | take back the last move          |
| POST   | `/api/new`    | `{"w":"Dad","b":"Noah"}` | start a new game (names optional) |
| POST   | `/api/names`  | `{"w":"Dad","b":"Noah"}` | set player names                 |

State shape: `{fen, turn, lastMove, status, moves, names, canUndo, version}`
where `status` ∈ `ongoing | check | checkmate | draw`.

Move legality, check, checkmate, stalemate, and the fifty-move rule are decided
by the rules brain from the FEN; **threefold repetition** is tracked by the
server across the game's history.

## Notes

- No third-party packages — Python 3 standard library only, so deploying to the
  VPS is just copying files and running `make` + `python3 server/server.py`.
- CORS is open (`*`) so a GitHub Pages frontend can talk to this server on a
  different origin. When the frontend is served over HTTPS, the server must be
  reached over HTTPS/`wss` too (put it behind a TLS reverse proxy).
- One shared game, no color locking yet: either device can make the move for
  the side to move (matches the calm pass-and-play feel). Per-device color
  locking is a possible later refinement.
