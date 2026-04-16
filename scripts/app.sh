#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# app.sh — Consumer lifecycle manager for autoresearch-quantum
#
# Usage:
#   bash scripts/app.sh bootstrap     Create venv, install deps, verify
#   bash scripts/app.sh start         Launch JupyterLab (opens browser)
#   bash scripts/app.sh start --no-open       Launch without opening browser
#   bash scripts/app.sh start --foreground    Run in foreground (Ctrl-C to stop)
#   bash scripts/app.sh start --port 9999     Use a specific port
#   bash scripts/app.sh stop           Stop running JupyterLab
#   bash scripts/app.sh restart        Stop + start
#   bash scripts/app.sh status         Show service status
#   bash scripts/app.sh validate       Run full validation suite
#   bash scripts/app.sh validate --quick  Lint + unit tests only
#   bash scripts/app.sh logs           Tail JupyterLab logs
#   bash scripts/app.sh logs -f        Follow live output
#   bash scripts/app.sh reset          Reset learner progress files
#   bash scripts/app.sh reset-state    Reset Jupyter runtime + UI state
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON="$VENV_DIR/bin/python"
JUPYTER="$VENV_DIR/bin/jupyter"

# ── Isolated Jupyter directories (prevents cross-project interference) ──
LOG_DIR="$PROJECT_ROOT/.logs"
PID_FILE="$LOG_DIR/jupyter.pid"
LOG_FILE="$LOG_DIR/jupyterlab.log"
JUPYTER_CONFIG_DIR="$PROJECT_ROOT/.jupyter_config"
JUPYTER_DATA_DIR="$PROJECT_ROOT/.jupyter_data"
JUPYTER_RUNTIME_DIR="$PROJECT_ROOT/.jupyter_runtime"
IPYTHONDIR="$PROJECT_ROOT/.ipython"
MPLCONFIGDIR="$PROJECT_ROOT/.cache/matplotlib"

# ── Colours ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[  ok]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ── Helpers ───────────────────────────────────────────────────────────

ensure_dirs() {
    mkdir -p "$LOG_DIR" "$JUPYTER_CONFIG_DIR" "$JUPYTER_DATA_DIR" \
             "$JUPYTER_RUNTIME_DIR" "$IPYTHONDIR" "$MPLCONFIGDIR"
}

set_jupyter_env() {
    export JUPYTER_CONFIG_DIR
    export JUPYTER_DATA_DIR
    export JUPYTER_RUNTIME_DIR
    export IPYTHONDIR
    export MPLCONFIGDIR
}

# Check if a PID is alive
_pid_alive() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

# Get the PID from our PID file, if any and alive
_get_running_pid() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if [[ -n "$pid" ]] && _pid_alive "$pid"; then
            echo "$pid"
            return 0
        fi
    fi
    return 1
}

# Find server URL from runtime JSON files (the Jupyter-native way)
_server_url() {
    "$PYTHON" -c '
import json, sys
from pathlib import Path

runtime = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve()
best = None
for path in sorted(runtime.glob("jpserver-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    pid = data.get("pid", -1)
    try:
        import os
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, TypeError):
        continue
    url = data.get("url", "").rstrip("/")
    token = data.get("token", "")
    entry = "/lab/tree/00_START_HERE.ipynb"
    if token:
        print(f"{url}{entry}?token={token}")
    else:
        print(f"{url}{entry}")
    sys.exit(0)

sys.exit(1)
' "$JUPYTER_RUNTIME_DIR" "$PROJECT_ROOT" 2>/dev/null
}

# Clean up stale runtime JSON files (process no longer running)
_cleanup_stale_runtime() {
    "$PYTHON" -c '
import json, os
from pathlib import Path

runtime = Path("'"$JUPYTER_RUNTIME_DIR"'")
for path in runtime.glob("jpserver-*.json"):
    try:
        data = json.loads(path.read_text())
        pid = int(data.get("pid", -1))
        os.kill(pid, 0)
    except (ProcessLookupError, ValueError, KeyError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        html = path.with_name(f"{path.stem}-open.html")
        html.unlink(missing_ok=True)
    except PermissionError:
        pass  # process exists but owned by another user
' 2>/dev/null || true
}

# ── Bootstrap ─────────────────────────────────────────────────────────
cmd_bootstrap() {
    info "Bootstrapping autoresearch-quantum..."

    # Python version check
    local py_cmd
    for candidate in python3.12 python3.11 python3; do
        if command -v "$candidate" &>/dev/null; then
            py_cmd="$candidate"
            break
        fi
    done
    if [[ -z "${py_cmd:-}" ]]; then
        fail "Python 3.11+ not found. Install Python first."
        exit 1
    fi

    local py_version
    py_version=$("$py_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)
    if (( py_major < 3 || py_minor < 11 )); then
        fail "Python >= 3.11 required (found $py_version)"
        exit 1
    fi
    ok "Python $py_version ($py_cmd)"

    # Create venv
    if [[ ! -d "$VENV_DIR" ]]; then
        info "Creating virtual environment..."
        "$py_cmd" -m venv "$VENV_DIR"
        ok "Virtual environment created"
    else
        ok "Virtual environment exists"
    fi

    # Install package
    info "Installing autoresearch-quantum + dependencies..."
    "$PYTHON" -m pip install --upgrade pip --quiet
    "$PYTHON" -m pip install -e "$PROJECT_ROOT[dev,notebooks]" --quiet
    ok "Package installed"

    # Create isolated Jupyter directories
    ensure_dirs

    # Install Jupyter kernel (into the venv, not user-global)
    set_jupyter_env
    "$PYTHON" -m ipykernel install \
        --sys-prefix \
        --name autoresearch-quantum \
        --display-name "Autoresearch Quantum" \
        --env IPYTHONDIR "$IPYTHONDIR" \
        --env MPLCONFIGDIR "$MPLCONFIGDIR" \
        2>/dev/null || true
    ok "Jupyter kernel registered (venv-local)"

    # Verify imports
    if "$PYTHON" -c "from autoresearch_quantum.models import ExperimentSpec; print('Import OK')" &>/dev/null; then
        ok "Import verification passed"
    else
        fail "Import verification failed — check installation"
        exit 1
    fi

    echo ""
    ok "${BOLD}Bootstrap complete!${NC}"
    echo ""
    echo "  Next steps:"
    echo "    bash scripts/app.sh start       # Launch JupyterLab"
    echo "    bash scripts/app.sh validate     # Run validation suite"
}

# ── Start ─────────────────────────────────────────────────────────────
cmd_start() {
    local open_browser=true
    local foreground=false
    local requested_port=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-open)    open_browser=false; shift ;;
            --foreground) foreground=true; shift ;;
            --port)
                [[ $# -ge 2 ]] || { fail "--port requires a value"; exit 1; }
                requested_port="$2"; shift 2 ;;
            *) fail "Unknown start option: $1"; exit 1 ;;
        esac
    done

    if [[ ! -f "$PYTHON" ]]; then
        fail "Not bootstrapped. Run: bash scripts/app.sh bootstrap"
        exit 1
    fi

    ensure_dirs
    set_jupyter_env
    _cleanup_stale_runtime

    # Check if already running
    local existing_pid
    if existing_pid=$(_get_running_pid); then
        local url
        url=$(_server_url || echo "http://localhost:8888/lab/tree/00_START_HERE.ipynb")
        warn "JupyterLab already running (PID $existing_pid)"
        echo ""
        echo "  $url"
        echo ""
        echo "  To stop:   bash scripts/app.sh stop"
        echo "  To restart: bash scripts/app.sh restart"
        if $open_browser; then
            if command -v open &>/dev/null; then
                open "$url"
            elif command -v xdg-open &>/dev/null; then
                xdg-open "$url"
            fi
        fi
        return 0
    fi

    # Find free port
    local port="${requested_port:-8888}"
    if [[ -z "$requested_port" ]]; then
        while lsof -i :"$port" &>/dev/null; do
            port=$((port + 1))
            if (( port > 8899 )); then
                fail "No free port in range 8888–8899"
                fail "Check for orphan Jupyter processes: lsof -i :8888"
                exit 1
            fi
        done
    fi

    # Foreground mode — Ctrl-C stops the server cleanly
    if $foreground; then
        info "Starting JupyterLab on port $port (foreground mode)..."
        local url="http://localhost:$port/lab/tree/00_START_HERE.ipynb"
        echo ""
        echo "  ${BOLD}$url${NC}"
        echo ""
        echo "  Jupyter is running in the foreground — this terminal is occupied."
        echo "  Press Ctrl-C to stop. Closing this terminal also stops Jupyter."
        echo ""
        if $open_browser; then
            # Open browser after a short delay (in background)
            (sleep 3 && {
                if command -v open &>/dev/null; then
                    open "$url"
                elif command -v xdg-open &>/dev/null; then
                    xdg-open "$url"
                fi
            }) &
        fi
        # exec replaces this shell — Ctrl-C goes straight to Jupyter
        exec "$JUPYTER" lab \
            --port="$port" \
            --no-browser \
            --ip=127.0.0.1 \
            --notebook-dir="$PROJECT_ROOT/notebooks"
    fi

    # Background mode — PID tracked, survives shell close
    info "Starting JupyterLab on port $port..."

    cd "$PROJECT_ROOT"
    : > "$LOG_FILE"
    nohup "$JUPYTER" lab \
        --port="$port" \
        --no-browser \
        --ip=127.0.0.1 \
        --notebook-dir="$PROJECT_ROOT/notebooks" \
        --ServerApp.token='' \
        --ServerApp.password='' \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait for server to start (check both port and runtime JSON)
    local tries=0
    while ! curl -s "http://localhost:$port/api" &>/dev/null; do
        sleep 0.5
        tries=$((tries + 1))
        if (( tries > 40 )); then
            fail "JupyterLab failed to start. Check: cat $LOG_FILE"
            exit 1
        fi
        # Check if the process died
        if ! _pid_alive "$pid"; then
            fail "JupyterLab exited during startup. Recent log output:"
            tail -n 20 "$LOG_FILE" >&2 || true
            rm -f "$PID_FILE"
            exit 1
        fi
    done

    local url="http://localhost:$port/lab/tree/00_START_HERE.ipynb"
    ok "JupyterLab running (PID $pid) on port $port"
    echo ""
    echo "  ${BOLD}$url${NC}"
    echo ""
    echo "  Jupyter is running in the background — this terminal is free."
    echo "  It will keep running even if you close this terminal."
    echo ""
    echo "  To stop:   bash scripts/app.sh stop"
    echo "  To check:  bash scripts/app.sh status"
    echo "  Logs:      bash scripts/app.sh logs -f"
    echo ""

    if $open_browser; then
        if command -v open &>/dev/null; then
            open "$url"
        elif command -v xdg-open &>/dev/null; then
            xdg-open "$url"
        fi
    fi
}

# ── Stop ──────────────────────────────────────────────────────────────
cmd_stop() {
    _cleanup_stale_runtime

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if _pid_alive "$pid"; then
            kill -TERM "$pid"
            # Wait for graceful shutdown (up to 10 seconds)
            local i=0
            while _pid_alive "$pid" && (( i < 20 )); do
                sleep 0.5
                i=$((i + 1))
            done
            if _pid_alive "$pid"; then
                warn "Process $pid did not stop gracefully, sending SIGKILL"
                kill -KILL "$pid" 2>/dev/null || true
            fi
            ok "JupyterLab stopped (PID $pid)"
        else
            warn "PID $pid not running (stale pid file)"
        fi
        rm -f "$PID_FILE"
    else
        warn "No PID file — JupyterLab not managed by app.sh"
        # Try to find and report any orphan Jupyter processes for this project
        local orphans
        orphans=$(ps aux | grep "[j]upyter.*--notebook-dir.*$PROJECT_ROOT" | awk '{print $2}' || true)
        if [[ -n "$orphans" ]]; then
            warn "Found possible orphan Jupyter process(es): $orphans"
            echo "  To stop them: kill $orphans"
        fi
    fi

    _cleanup_stale_runtime
}

# ── Restart ───────────────────────────────────────────────────────────
cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start "$@"
}

# ── Status ────────────────────────────────────────────────────────────
cmd_status() {
    echo ""
    echo "  ${BOLD}autoresearch-quantum${NC}"
    echo "  Root: $PROJECT_ROOT"
    echo ""

    # Git
    if command -v git &>/dev/null && [[ -d "$PROJECT_ROOT/.git" ]]; then
        local branch commit
        branch=$(cd "$PROJECT_ROOT" && git branch --show-current 2>/dev/null || echo "?")
        commit=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "?")
        ok "Git: $branch @ $commit"
    fi

    # Venv
    if [[ -f "$PYTHON" ]]; then
        local py_ver
        py_ver=$("$PYTHON" --version 2>&1)
        ok "Virtual environment: $py_ver"
    else
        fail "Virtual environment: not found"
    fi

    # JupyterLab
    _cleanup_stale_runtime
    local running_pid
    if running_pid=$(_get_running_pid); then
        local url
        url=$(_server_url || echo "(could not determine URL)")
        ok "JupyterLab: running (PID $running_pid)"
        echo "       URL: $url"
        echo "       Log: $LOG_FILE"
    else
        warn "JupyterLab: not running"
        # Check for orphans
        local orphans
        orphans=$(ps aux | grep "[j]upyter.*--notebook-dir.*$PROJECT_ROOT" | awk '{print $2}' || true)
        if [[ -n "$orphans" ]]; then
            warn "  Orphan process(es) detected: $orphans"
            echo "       Stop them: kill $orphans"
        fi
    fi

    # Port scan
    local ports_in_use=""
    for p in $(seq 8888 8899); do
        if lsof -i :"$p" &>/dev/null; then
            local owner
            owner=$(lsof -ti :"$p" 2>/dev/null | head -1)
            ports_in_use="$ports_in_use $p(pid:$owner)"
        fi
    done
    if [[ -n "$ports_in_use" ]]; then
        info "Ports in use:$ports_in_use"
    fi

    # Notebooks
    local nb_count
    nb_count=$(find "$PROJECT_ROOT/notebooks" -name "*.ipynb" | wc -l | tr -d ' ')
    ok "Notebooks: $nb_count found"

    # Learner progress
    local progress_count
    progress_count=$(find "$PROJECT_ROOT" -name "*_progress.json" 2>/dev/null | wc -l | tr -d ' ')
    if (( progress_count > 0 )); then
        ok "Learner progress files: $progress_count"
    else
        info "Learner progress files: none (fresh start)"
    fi

    echo ""
}

# ── Validate ──────────────────────────────────────────────────────────
cmd_validate() {
    local mode="${1:---standard}"

    if [[ ! -f "$PYTHON" ]]; then
        fail "Not bootstrapped. Run: bash scripts/app.sh bootstrap"
        exit 1
    fi

    echo ""
    info "${BOLD}Running validation ($mode)...${NC}"
    echo ""

    local failed=0

    # Ruff
    info "Ruff lint..."
    if "$VENV_DIR/bin/ruff" check src/ tests/ scripts/ --quiet; then
        ok "Ruff: clean"
    else
        fail "Ruff: errors found"
        failed=1
    fi

    # Mypy
    info "Mypy type check..."
    if "$PYTHON" -m mypy src/autoresearch_quantum/ --no-error-summary 2>/dev/null; then
        ok "Mypy: clean"
    else
        fail "Mypy: type errors found"
        failed=1
    fi

    if [[ "$mode" == "--quick" ]]; then
        # Quick: unit tests only (no notebook execution)
        info "Unit tests (quick)..."
        if "$PYTHON" -m pytest tests/ -k "not test_notebook_executes and not test_browser" -q --tb=short --no-header 2>&1; then
            ok "Unit tests: passed"
        else
            fail "Unit tests: failures"
            failed=1
        fi
    else
        # Standard: all tests except browser UX
        info "Full test suite..."
        if "$PYTHON" -m pytest tests/ -k "not test_browser" -v --tb=short --no-header 2>&1; then
            ok "Tests: passed"
        else
            fail "Tests: failures"
            failed=1
        fi
    fi

    echo ""
    if (( failed == 0 )); then
        ok "${BOLD}All validation checks passed.${NC}"
    else
        fail "${BOLD}Some checks failed — see above.${NC}"
        exit 1
    fi
}

# ── Logs ──────────────────────────────────────────────────────────────
cmd_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        if [[ "${1:-}" == "-f" || "${1:-}" == "--follow" ]]; then
            tail -f "$LOG_FILE"
        else
            tail -n 80 "$LOG_FILE"
        fi
    else
        warn "No log file found. Start JupyterLab first."
    fi
}

# ── Reset (learner progress) ─────────────────────────────────────────
cmd_reset() {
    info "Resetting learner progress..."
    local count=0
    while IFS= read -r -d '' f; do
        rm "$f"
        count=$((count + 1))
    done < <(find "$PROJECT_ROOT" -name "*_progress.json" -print0 2>/dev/null)
    ok "Removed $count progress file(s)"
    info "Notebook outputs are preserved (use nbstripout to clear them)"
}

# ── Reset State (Jupyter runtime + UI state) ─────────────────────────
cmd_reset_state() {
    # Stop server first if running
    local running_pid
    if running_pid=$(_get_running_pid 2>/dev/null); then
        info "Stopping running server first..."
        cmd_stop
    fi

    info "Cleaning Jupyter runtime state..."
    local count=0

    # Runtime JSON files
    for f in "$JUPYTER_RUNTIME_DIR"/jpserver-*.json "$JUPYTER_RUNTIME_DIR"/jpserver-*-open.html \
             "$JUPYTER_RUNTIME_DIR"/kernel-*.json; do
        if [[ -f "$f" ]]; then
            rm "$f"
            count=$((count + 1))
        fi
    done

    # Saved UI state (workspaces, trust DB)
    for f in "$JUPYTER_DATA_DIR/nbsignatures.db" "$JUPYTER_DATA_DIR/notebook_secret"; do
        if [[ -f "$f" ]]; then
            rm "$f"
            count=$((count + 1))
        fi
    done
    if [[ -d "$JUPYTER_DATA_DIR/lab/workspaces" ]]; then
        local ws_count
        ws_count=$(find "$JUPYTER_DATA_DIR/lab/workspaces" -name "*.jupyterlab-workspace" 2>/dev/null | wc -l | tr -d ' ')
        if (( ws_count > 0 )); then
            find "$JUPYTER_DATA_DIR/lab/workspaces" -name "*.jupyterlab-workspace" -delete
            count=$((count + ws_count))
        fi
    fi

    # PID file
    rm -f "$PID_FILE"

    ok "Removed $count runtime/state file(s)"
    info "JupyterLab will start fresh on next launch"
}

# ── Main dispatch ─────────────────────────────────────────────────────
case "${1:-help}" in
    bootstrap)  cmd_bootstrap ;;
    start)      shift; cmd_start "$@" ;;
    stop)       cmd_stop ;;
    restart)    shift; cmd_restart "$@" ;;
    status)     cmd_status ;;
    validate)   cmd_validate "${2:-}" ;;
    logs)       cmd_logs "${2:-}" ;;
    reset)      cmd_reset ;;
    reset-state) cmd_reset_state ;;
    help|--help|-h)
        echo ""
        echo "  ${BOLD}autoresearch-quantum${NC} — lifecycle manager"
        echo ""
        echo "  Usage: bash scripts/app.sh <command>"
        echo ""
        echo "  Commands:"
        echo "    bootstrap            Create venv, install deps, verify imports"
        echo "    start [options]      Launch JupyterLab"
        echo "      --no-open            Don't open browser"
        echo "      --foreground         Run in foreground (Ctrl-C to stop)"
        echo "      --port PORT          Use a specific port"
        echo "    stop                 Stop JupyterLab"
        echo "    restart [options]    Stop + start (same options as start)"
        echo "    status               Show service and project status"
        echo "    validate [--quick]   Run lint, type check, and tests"
        echo "    logs [-f]            Show or follow JupyterLab output"
        echo "    reset                Delete learner progress files"
        echo "    reset-state          Reset Jupyter runtime + UI state"
        echo ""
        ;;
    *)
        fail "Unknown command: $1"
        echo "  Run 'bash scripts/app.sh help' for usage."
        exit 1
        ;;
esac
