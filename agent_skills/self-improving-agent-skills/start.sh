#!/usr/bin/env bash
#
# Starts the Self-Improving Agent Skills dashboard (FastAPI backend + Next.js frontend).
#
# Usage:
#   ./start.sh                 # install deps if needed, then run both servers
#   ./start.sh --setup-only    # install dependencies and exit
#
# Override ports with BACKEND_PORT / FRONTEND_PORT. Ctrl+C stops both servers.
#
# While running, this script supervises both servers: the dashboard's restart and
# shutdown buttons drop a request in .run/request, which the loop below picks up.

set -euo pipefail

# Job control puts each background server in its own process group, so shutdown can
# kill a whole tree. Without it, `npm run dev` leaves its `next dev` child orphaned
# and holding the port.
set -m

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKEND_DIR="$ROOT_DIR/backend"
readonly FRONTEND_DIR="$ROOT_DIR/frontend"
readonly VENV_DIR="$BACKEND_DIR/venv"
readonly DEPS_STAMP="$VENV_DIR/.requirements-stamp"

readonly BACKEND_PORT="${BACKEND_PORT:-8891}"
readonly FRONTEND_PORT="${FRONTEND_PORT:-3000}"
readonly HEALTH_TIMEOUT_SECONDS=60
readonly SHUTDOWN_GRACE_SECONDS=5
readonly PORT_RELEASE_TIMEOUT_SECONDS=10

# Shared with backend/service_control.py, which writes the request file.
readonly RUN_DIR="$ROOT_DIR/.run"
readonly SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"
readonly REQUEST_FILE="$RUN_DIR/request"

backend_pid=""
frontend_pid=""

log()  { printf '\033[0;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[0;33m==>\033[0m %s\n' "$1"; }
die()  { printf '\033[0;31mError:\033[0m %s\n' "$1" >&2; exit 1; }

# Signals the server's whole process group (negative PID), falling back to the bare
# PID, so helper children such as `next dev` go down with their parent.
signal_tree() {
  local signal="$1" pid="$2"
  [[ -n "$pid" ]] || return 0
  kill "-$signal" "-$pid" 2>/dev/null || kill "-$signal" "$pid" 2>/dev/null || true
}

is_running() {
  [[ -n "$1" ]] && kill -0 "$1" 2>/dev/null
}

stop_servers() {
  signal_tree TERM "$frontend_pid"
  signal_tree TERM "$backend_pid"

  for ((i = 0; i < SHUTDOWN_GRACE_SECONDS; i++)); do
    is_running "$frontend_pid" || is_running "$backend_pid" || break
    sleep 1
  done

  # Anything still alive after the grace period gets forced.
  is_running "$frontend_pid" && signal_tree KILL "$frontend_pid" || true
  is_running "$backend_pid" && signal_tree KILL "$backend_pid" || true

  wait 2>/dev/null || true
  backend_pid=""
  frontend_pid=""
}

cleanup() {
  trap - INT TERM EXIT
  log "Shutting down..."
  stop_servers
  rm -f "$SUPERVISOR_PID_FILE" "$REQUEST_FILE"
}

check_prerequisites() {
  command -v python3 >/dev/null || die "python3 not found. Install Python 3.10 or newer."
  command -v npm >/dev/null || die "npm not found. Install Node.js 18 or newer from https://nodejs.org"
}

is_port_in_use() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

check_ports_free() {
  for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    if is_port_in_use "$port"; then
      die "Port $port is already in use. Stop that process, or rerun with a different port:
  BACKEND_PORT=8892 FRONTEND_PORT=3001 ./start.sh"
    fi
  done
}

# Reinstalls only when requirements.txt has changed since the last successful install.
install_backend_deps() {
  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
  fi

  local requirements="$BACKEND_DIR/requirements.txt"
  if [[ -f "$DEPS_STAMP" ]] && diff -q "$requirements" "$DEPS_STAMP" >/dev/null 2>&1; then
    log "Backend dependencies up to date."
    return
  fi

  log "Installing backend dependencies..."
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip
  "$VENV_DIR/bin/pip" install --quiet -r "$requirements"
  cp "$requirements" "$DEPS_STAMP"
}

install_frontend_deps() {
  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    log "Frontend dependencies up to date."
    return
  fi

  log "Installing frontend dependencies..."
  npm install --prefix "$FRONTEND_DIR" --no-audit --no-fund
}

wait_for_backend() {
  log "Waiting for backend to become healthy..."
  for ((i = 0; i < HEALTH_TIMEOUT_SECONDS; i++)); do
    if curl --silent --fail "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
      log "Backend ready on http://localhost:$BACKEND_PORT"
      return 0
    fi
    if ! kill -0 "$backend_pid" 2>/dev/null; then
      warn "Backend exited during startup. Check the output above for the cause."
      return 1
    fi
    sleep 1
  done
  warn "Backend did not respond within ${HEALTH_TIMEOUT_SECONDS}s."
  return 1
}

# A just-killed server can hold its port for a moment; restarting into it would
# fail or, worse, silently land the frontend on a different port.
wait_for_ports_free() {
  for ((i = 0; i < PORT_RELEASE_TIMEOUT_SECONDS; i++)); do
    if ! is_port_in_use "$BACKEND_PORT" && ! is_port_in_use "$FRONTEND_PORT"; then
      return 0
    fi
    sleep 1
  done
  warn "Ports $BACKEND_PORT/$FRONTEND_PORT are still busy after ${PORT_RELEASE_TIMEOUT_SECONDS}s."
  return 1
}

start_backend() {
  log "Starting backend on port $BACKEND_PORT..."
  (cd "$BACKEND_DIR" && exec "$VENV_DIR/bin/python" -m uvicorn app:app --host 0.0.0.0 --port "$BACKEND_PORT") &
  backend_pid=$!
}

start_frontend() {
  log "Starting frontend on port $FRONTEND_PORT..."
  NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" \
    npm run dev --prefix "$FRONTEND_DIR" -- --port "$FRONTEND_PORT" &
  frontend_pid=$!
}

# Reads and clears the pending request in one step, so a slow restart cannot
# replay the same request on the next pass.
take_request() {
  [[ -f "$REQUEST_FILE" ]] || return 0
  local request
  request="$(tr -d '[:space:]' < "$REQUEST_FILE" 2>/dev/null || true)"
  rm -f "$REQUEST_FILE"
  printf '%s' "$request"
}

restart_servers() {
  log "Restart requested from the dashboard."
  stop_servers
  wait_for_ports_free || return 1
  start_backend
  wait_for_backend || return 1
  start_frontend
  log "Restarted. Dashboard running at http://localhost:$FRONTEND_PORT"
}

# Watches both servers and the dashboard's control file until something asks to
# stop, or a server dies on its own.
supervise() {
  while true; do
    case "$(take_request)" in
      restart)
        restart_servers || return 1
        ;;
      shutdown)
        log "Shutdown requested from the dashboard."
        return 0
        ;;
      "")
        ;;
      *)
        warn "Ignoring unrecognized control request."
        ;;
    esac

    if ! is_running "$backend_pid" || ! is_running "$frontend_pid"; then
      warn "A server stopped unexpectedly."
      return 1
    fi

    # Polled rather than `wait -n`, which macOS's stock bash 3.2 does not support.
    sleep 1
  done
}

main() {
  check_prerequisites
  install_backend_deps
  install_frontend_deps

  if [[ "${1:-}" == "--setup-only" ]]; then
    log "Setup complete. Run ./start.sh to launch the dashboard."
    return
  fi

  check_ports_free
  trap 'cleanup; exit 0' INT TERM
  trap cleanup EXIT

  # A request left behind by a previous run would fire immediately otherwise.
  mkdir -p "$RUN_DIR"
  rm -f "$REQUEST_FILE"
  echo "$$" > "$SUPERVISOR_PID_FILE"

  start_backend
  wait_for_backend || die "Backend failed to start."
  start_frontend

  echo
  log "Dashboard running at http://localhost:$FRONTEND_PORT"
  warn "Add your Gemini API key in the UI: https://aistudio.google.com/apikey"
  log "Press Ctrl+C to stop both servers, or use the buttons in the dashboard header."
  echo

  # Exits as soon as either server dies so we never leave a half-running stack.
  supervise || exit 1
  exit 0
}

main "$@"
