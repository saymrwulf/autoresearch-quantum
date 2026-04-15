#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# app.sh — Consumer lifecycle manager for autoresearch-quantum
#
# Usage:
#   bash scripts/app.sh bootstrap     Create venv, install deps, verify
#   bash scripts/app.sh start         Launch JupyterLab (opens browser)
#   bash scripts/app.sh start --no-open  Launch without opening browser
#   bash scripts/app.sh stop           Stop running JupyterLab
#   bash scripts/app.sh status         Show service status
#   bash scripts/app.sh validate       Run full validation suite
#   bash scripts/app.sh validate --quick  Lint + unit tests only
#   bash scripts/app.sh logs           Tail JupyterLab logs
#   bash scripts/app.sh reset          Reset learner progress files
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
LOG_DIR="$PROJECT_ROOT/.logs"
PID_FILE="$LOG_DIR/jupyter.pid"
LOG_FILE="$LOG_DIR/jupyterlab.log"
PYTHON="$VENV_DIR/bin/python"
JUPYTER="$VENV_DIR/bin/jupyter"

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

    # Install Jupyter kernel
    "$PYTHON" -m ipykernel install --user --name autoresearch-quantum --display-name "Autoresearch Quantum" --quiet 2>/dev/null || true
    ok "Jupyter kernel registered"

    # Create log directory
    mkdir -p "$LOG_DIR"

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
    [[ "${1:-}" == "--no-open" ]] && open_browser=false

    if [[ ! -f "$PYTHON" ]]; then
        fail "Not bootstrapped. Run: bash scripts/app.sh bootstrap"
        exit 1
    fi

    # Check if already running
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        local url
        url=$(grep -o 'http://[^ ]*' "$LOG_FILE" 2>/dev/null | tail -1 || echo "http://localhost:8888")
        warn "JupyterLab already running (PID $(cat "$PID_FILE"))"
        echo "  $url"
        return 0
    fi

    mkdir -p "$LOG_DIR"

    # Find free port
    local port=8888
    while lsof -i :"$port" &>/dev/null; do
        port=$((port + 1))
        if (( port > 8899 )); then
            fail "No free port in range 8888–8899"
            exit 1
        fi
    done

    info "Starting JupyterLab on port $port..."

    cd "$PROJECT_ROOT"
    nohup "$JUPYTER" lab \
        --port="$port" \
        --no-browser \
        --notebook-dir="$PROJECT_ROOT/notebooks" \
        --ServerApp.token='' \
        --ServerApp.password='' \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait for server to start
    local tries=0
    while ! curl -s "http://localhost:$port/api" &>/dev/null; do
        sleep 0.5
        tries=$((tries + 1))
        if (( tries > 20 )); then
            fail "JupyterLab failed to start. Check: cat $LOG_FILE"
            exit 1
        fi
    done

    local url="http://localhost:$port/lab/tree/00_START_HERE.ipynb"
    ok "JupyterLab running (PID $pid)"
    echo ""
    echo "  ${BOLD}$url${NC}"
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
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            ok "JupyterLab stopped (PID $pid)"
        else
            warn "PID $pid not running (stale pid file)"
        fi
        rm -f "$PID_FILE"
    else
        warn "No PID file — JupyterLab not managed by app.sh"
    fi
}

# ── Status ────────────────────────────────────────────────────────────
cmd_status() {
    echo ""
    echo "  ${BOLD}autoresearch-quantum${NC}"
    echo ""

    # Venv
    if [[ -f "$PYTHON" ]]; then
        local py_ver
        py_ver=$("$PYTHON" --version 2>&1)
        ok "Virtual environment: $py_ver"
    else
        fail "Virtual environment: not found"
    fi

    # JupyterLab
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        ok "JupyterLab: running (PID $(cat "$PID_FILE"))"
    else
        warn "JupyterLab: not running"
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
        tail -f "$LOG_FILE"
    else
        warn "No log file found. Start JupyterLab first."
    fi
}

# ── Reset ─────────────────────────────────────────────────────────────
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

# ── Main dispatch ─────────────────────────────────────────────────────
case "${1:-help}" in
    bootstrap)  cmd_bootstrap ;;
    start)      cmd_start "${2:-}" ;;
    stop)       cmd_stop ;;
    status)     cmd_status ;;
    validate)   cmd_validate "${2:-}" ;;
    logs)       cmd_logs ;;
    reset)      cmd_reset ;;
    help|--help|-h)
        echo ""
        echo "  ${BOLD}autoresearch-quantum${NC} — lifecycle manager"
        echo ""
        echo "  Usage: bash scripts/app.sh <command>"
        echo ""
        echo "  Commands:"
        echo "    bootstrap          Create venv, install deps, verify imports"
        echo "    start [--no-open]  Launch JupyterLab (opens 00_START_HERE.ipynb)"
        echo "    stop               Stop JupyterLab"
        echo "    status             Show service and project status"
        echo "    validate [--quick] Run lint, type check, and tests"
        echo "    logs               Tail JupyterLab output"
        echo "    reset              Delete learner progress files"
        echo ""
        ;;
    *)
        fail "Unknown command: $1"
        echo "  Run 'bash scripts/app.sh help' for usage."
        exit 1
        ;;
esac
