#!/usr/bin/env bash
set -euo pipefail

print_help() {
  cat <<'EOF'
Usage: AI_first/scripts/start_ai_first.sh [options]

Starts both servers:
  - Web server (serves HTML) on port 8000
  - Control server (API + run buttons) on port 8790

Options:
  --web-port PORT        Web server port (default: 8000)
  --api-port PORT        Control server port (default: 8790)
  --python PATH          Python interpreter to use (default: .venv/bin/python if present, else python3)
  -h, --help             Show this help
EOF
}

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
web_port="8000"
api_port="8790"
python_bin=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --web-port)
      web_port="${2:-}"
      shift 2
      ;;
    --api-port)
      api_port="${2:-}"
      shift 2
      ;;
    --python)
      python_bin="${2:-}"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_help
      exit 1
      ;;
  esac
done

cd "$root"

if [[ -n "$python_bin" ]]; then
  if [[ "$python_bin" == */* || "$python_bin" == .* ]]; then
    if [[ ! -x "$python_bin" ]]; then
      echo "Warning: $python_bin not found or not executable; falling back." >&2
      python_bin=""
    fi
  fi
fi

if [[ -z "$python_bin" ]]; then
  if [[ -x "$root/.venv/bin/python" ]]; then
    python_bin="$root/.venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cmd_api=("$python_bin" AI_first/scripts/ai_first_control_server.py --port "$api_port")

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting AI_first control server on http://127.0.0.1:${api_port} ..."
"${cmd_api[@]}" &
api_pid=$!
sleep 0.2
if ! kill -0 "$api_pid" 2>/dev/null; then
  echo "Control server failed to start." >&2
  exit 1
fi

echo "Starting web server on http://127.0.0.1:${web_port} ..."
"$python_bin" -m http.server "$web_port" --directory . &
web_pid=$!
sleep 0.2
if ! kill -0 "$web_pid" 2>/dev/null; then
  echo "Web server failed to start." >&2
  exit 1
fi

echo ""
echo "Starter page: http://127.0.0.1:${web_port}/AI_first/index.html"
echo "Dashboard:    http://127.0.0.1:${web_port}/AI_first/ui/ai_first_dashboard.html"
echo "Control API:  http://127.0.0.1:${api_port}/api/status"
echo "Press Ctrl+C to stop both servers."

wait
