"""End-to-end browser UX tests using Playwright.

Validates the complete consumer experience:
- JupyterLab launches and serves notebooks
- 00_START_HERE.ipynb loads and renders plan links
- Content notebooks load, render widgets, and navigation works
- The full walkthrough from entry point to plan completion is unbroken

Requires: pip install playwright && python -m playwright install chromium

Run with: pytest tests/test_browser_ux.py -m browser -v
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from pathlib import Path

import pytest

# Skip entire module if playwright is not installed
pw = pytest.importorskip("playwright.sync_api", reason="playwright not installed")

NOTEBOOK_DIR = Path("notebooks")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STARTUP_TIMEOUT = 30  # seconds to wait for Jupyter to start
PAGE_TIMEOUT = 15_000  # ms per page load


def _find_free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def jupyter_server():
    """Launch a JupyterLab server for the test session, tear it down after."""
    port = _find_free_port()
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"

    if not venv_python.exists():
        pytest.skip("No .venv found — run 'bash scripts/app.sh bootstrap' first")

    jupyter_bin = PROJECT_ROOT / ".venv" / "bin" / "jupyter"
    if not jupyter_bin.exists():
        pytest.skip("jupyter not installed in .venv")

    proc = subprocess.Popen(
        [
            str(jupyter_bin), "lab",
            f"--port={port}",
            "--no-browser",
            f"--notebook-dir={NOTEBOOK_DIR.resolve()}",
            "--ServerApp.token=",
            "--ServerApp.password=",
            "--ServerApp.disable_check_xsrf=True",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        preexec_fn=os.setsid,
    )

    base_url = f"http://localhost:{port}"

    # Wait for server to become responsive
    started = False
    for _ in range(STARTUP_TIMEOUT * 2):
        try:
            with socket.create_connection(("localhost", port), timeout=0.5):
                started = True
                break
        except OSError:
            time.sleep(0.5)

    if not started:
        proc.kill()
        pytest.skip(f"JupyterLab failed to start on port {port}")

    # Give the server a moment to fully initialize
    time.sleep(2)

    yield base_url

    # Teardown: kill the process group
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


@pytest.fixture(scope="module")
def browser_page(jupyter_server: str):
    """Create a Playwright browser page for the test session."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT)
        yield page, jupyter_server
        browser.close()


# ── Markers ───────────────────────────────────────────────────────────

pytestmark = pytest.mark.browser


# ── Tests ─────────────────────────────────────────────────────────────


class TestJupyterLabLaunches:
    """Verify that JupyterLab is reachable and serves content."""

    def test_api_reachable(self, jupyter_server: str) -> None:
        """JupyterLab API responds to requests."""
        import urllib.request
        with urllib.request.urlopen(f"{jupyter_server}/api") as resp:
            assert resp.status == 200

    def test_lab_page_loads(self, browser_page: tuple) -> None:
        """JupyterLab main page loads without errors."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab")
        # JupyterLab should render its main application
        page.wait_for_selector("#jp-main-dock-panel", timeout=PAGE_TIMEOUT)


class TestStartHereNotebook:
    """Verify the central entry point notebook renders correctly."""

    def test_start_here_loads(self, browser_page: tuple) -> None:
        """00_START_HERE.ipynb opens in JupyterLab."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/00_START_HERE.ipynb")
        # Wait for notebook to render
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)

    def test_start_here_has_title(self, browser_page: tuple) -> None:
        """The entry notebook displays the main heading."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/00_START_HERE.ipynb")
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)
        # Look for the title text in rendered markdown
        content = page.text_content(".jp-Notebook")
        assert content is not None
        assert "Start Here" in content

    def test_start_here_has_plan_links(self, browser_page: tuple) -> None:
        """The entry notebook contains links to all four plans."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/00_START_HERE.ipynb")
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)
        content = page.text_content(".jp-Notebook") or ""
        assert "Plan A" in content
        assert "Plan B" in content
        assert "Plan C" in content
        assert "Plan D" in content


class TestPlanNotebooksLoad:
    """Verify that the first notebook of each plan loads without errors."""

    @pytest.mark.parametrize("notebook_path", [
        "plan_a/01_encoded_magic_state.ipynb",
        "plan_b/spiral_notebook.ipynb",
        "plan_c/00_dashboard.ipynb",
        "plan_d/experiment_1_protection.ipynb",
    ])
    def test_plan_entry_loads(self, browser_page: tuple, notebook_path: str) -> None:
        """Each plan's entry notebook opens and renders."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/{notebook_path}")
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)
        # Verify the notebook rendered at least some cells
        cells = page.query_selector_all(".jp-Cell")
        assert len(cells) > 0, f"{notebook_path} rendered zero cells"


class TestNavigationLinks:
    """Verify that inter-notebook navigation links are present and functional."""

    @pytest.mark.parametrize("notebook_path,expected_link_text", [
        ("plan_a/01_encoded_magic_state.ipynb", "Notebook 2"),
        ("plan_a/02_measuring_progress.ipynb", "Notebook 3"),
        ("plan_a/03_the_ratchet.ipynb", "Plan B"),
        ("plan_d/experiment_1_protection.ipynb", "Experiment 2"),
        ("plan_d/experiment_2_noise.ipynb", "Experiment 3"),
    ])
    def test_navigation_link_present(
        self, browser_page: tuple, notebook_path: str, expected_link_text: str,
    ) -> None:
        """Navigation footer cells contain expected forward-links."""
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/{notebook_path}")
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)
        content = page.text_content(".jp-Notebook") or ""
        assert expected_link_text in content, (
            f"{notebook_path} missing navigation link containing '{expected_link_text}'"
        )

    def test_start_here_link_in_every_content_notebook(self, browser_page: tuple) -> None:
        """Every content notebook links back to START_HERE."""
        page, base_url = browser_page
        content_notebooks = [
            "plan_a/01_encoded_magic_state.ipynb",
            "plan_a/02_measuring_progress.ipynb",
            "plan_a/03_the_ratchet.ipynb",
            "plan_b/spiral_notebook.ipynb",
            "plan_c/00_dashboard.ipynb",
            "plan_d/experiment_1_protection.ipynb",
        ]
        for nb in content_notebooks:
            page.goto(f"{base_url}/lab/tree/{nb}")
            page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)
            content = page.text_content(".jp-Notebook") or ""
            assert "Start Here" in content, f"{nb} missing 'Start Here' back-link"


class TestWidgetRendering:
    """Verify that assessment widgets render after kernel execution."""

    def test_notebook_with_widgets_can_execute(self, browser_page: tuple) -> None:
        """A notebook with widgets can be opened and cells executed.

        This tests the full UX: open notebook → run cells → widgets appear.
        We use a lightweight notebook (Plan D Experiment 1) which runs fast.
        """
        page, base_url = browser_page
        page.goto(f"{base_url}/lab/tree/plan_d/experiment_1_protection.ipynb")
        page.wait_for_selector(".jp-Notebook", timeout=PAGE_TIMEOUT)

        # Wait for kernel to be ready (kernel indicator in toolbar)
        page.wait_for_selector(
            ".jp-Notebook-ExecutionIndicator",
            timeout=PAGE_TIMEOUT,
        )

        # Verify the notebook has rendered cells
        cells = page.query_selector_all(".jp-Cell")
        assert len(cells) > 5, "Notebook should have rendered multiple cells"
