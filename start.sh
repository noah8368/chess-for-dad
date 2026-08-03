#!/usr/bin/env bash
#
# Chess For Dad — start the live sync service.
#
# Builds the rules-brain binary if needed, then runs the Python sync server so
# two devices on the same network can play together. Stop it with Ctrl+C.
#
#   ./start.sh                 # serve on port 8000, all network interfaces
#   ./start.sh --port 9000     # pick a different port
#   ./start.sh --host 127.0.0.1

set -euo pipefail

usage() {
  cat <<'EOF'
Chess For Dad — start the live sync service.

Usage: ./start.sh [--port N] [--host ADDR]

  --port N     Port to serve on (default: 8000)
  --host ADDR  Interface to bind (default: all interfaces)
  -h, --help   Show this help

Builds the rules-brain binary if needed, then runs the Python sync server.
Open the printed URL on two devices on the same network to play. Ctrl+C stops it.
EOF
}

PORT=8000
HOST_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST_ARGS=(--host "$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# Run from the repo root, wherever the script was invoked from.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found." >&2
  exit 1
fi

# Build the rules brain if it is missing or any source is newer than the binary.
if [ ! -x ./chess-for-dad ] || [ -n "$(find src Makefile -newer ./chess-for-dad 2>/dev/null)" ]; then
  if ! command -v make >/dev/null 2>&1 || ! command -v g++ >/dev/null 2>&1; then
    echo "Error: 'make' and 'g++' are needed to build the chess-for-dad rules brain." >&2
    exit 1
  fi
  echo "Building the rules brain..."
  make
fi

# Best-effort LAN address so a second device knows where to connect.
lan_ip() {
  local ip=""
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')" || true
  if [ -z "$ip" ] && command -v ipconfig >/dev/null 2>&1; then
    local iface
    for iface in en0 en1 en2; do
      ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
      [ -n "$ip" ] && break
    done
  fi
  printf '%s' "$ip"
}
IP="$(lan_ip)"

echo
echo "  ♟  Chess For Dad is starting"
echo "  ─────────────────────────────"
echo "  On this device:    http://localhost:${PORT}"
if [ -n "$IP" ]; then
  echo "  On another device: http://${IP}:${PORT}   (same Wi-Fi / network)"
fi
echo "  Stop with Ctrl+C"
echo

# exec so Ctrl+C goes straight to the server for a clean shutdown.
exec python3 server/server.py --port "$PORT" ${HOST_ARGS[@]+"${HOST_ARGS[@]}"}
