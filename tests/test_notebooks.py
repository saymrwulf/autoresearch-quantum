"""Notebook execution tests — validates that all notebooks run without errors.

Uses nbclient to execute each notebook in a fresh kernel. This catches:
- Import errors
- Broken code cells
- Widget rendering failures
- API mismatches between notebooks and library code
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

NOTEBOOK_DIR = Path("notebooks")

ALL_NOTEBOOKS = sorted(NOTEBOOK_DIR.rglob("*.ipynb"))

# Execution timeout per cell (seconds) — noisy simulation cells can be slow
CELL_TIMEOUT = 180


def _notebook_id(path: Path) -> str:
    """Create a readable test ID from notebook path."""
    return str(path.relative_to(NOTEBOOK_DIR)).replace("/", "__").removesuffix(".ipynb")


@pytest.fixture(params=ALL_NOTEBOOKS, ids=[_notebook_id(p) for p in ALL_NOTEBOOKS])
def notebook_path(request):
    return request.param


def test_notebook_valid_json(notebook_path):
    """Notebook file is valid JSON and nbformat."""
    nb = nbformat.read(str(notebook_path), as_version=4)
    assert nb.nbformat == 4
    assert len(nb.cells) > 0


def test_notebook_has_code_cells(notebook_path):
    """Every notebook has at least one code cell."""
    nb = nbformat.read(str(notebook_path), as_version=4)
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert len(code_cells) > 0, f"{notebook_path} has no code cells"


def test_notebook_executes(notebook_path):
    """Execute the full notebook in a fresh kernel — no cell may raise."""
    nb = nbformat.read(str(notebook_path), as_version=4)
    # Normalize to add missing cell IDs (avoids nbformat warnings)
    _, nb = nbformat.validator.normalize(nb)

    # Set cwd to the notebook's directory so relative paths (e.g. ../../configs)
    # resolve correctly, matching how a student would run the notebook.
    nb_dir = str(notebook_path.resolve().parent)
    client = NotebookClient(
        nb,
        timeout=CELL_TIMEOUT,
        kernel_name="python3",
        resources={"metadata": {"path": nb_dir}},
    )
    try:
        client.execute()
    except CellExecutionError as exc:
        # Extract the failing cell for a clear error message
        pytest.fail(
            f"Notebook {notebook_path} failed during execution:\n"
            f"Cell index: {exc.cell_index if hasattr(exc, 'cell_index') else '?'}\n"
            f"{exc}"
        )


def test_notebook_quiz_cells_have_section(notebook_path):
    """Every quiz/predict/reflect/order call should specify a section= parameter.

    Without a section, tracker scores are all lumped into 'intro', making
    checkpoint_summary useless.
    """
    nb = nbformat.read(str(notebook_path), as_version=4)
    missing_section = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        src = "".join(cell.source)
        for fn in ["quiz(", "predict_choice(", "reflect(", "order("]:
            if fn in src and "section=" not in src and "tracker" in src and "LearningTracker" not in src:
                    missing_section.append((i, fn.rstrip("(")))
    if missing_section:
        details = ", ".join(f"cell {i} ({fn})" for i, fn in missing_section)
        warnings.warn(
            f"{notebook_path}: {len(missing_section)} assessment calls missing section= parameter: {details}",
            UserWarning,
            stacklevel=1,
        )


def test_learning_objectives_document_exists():
    """learning_objectives.md exists and covers all four plans."""
    obj_path = NOTEBOOK_DIR / "learning_objectives.md"
    assert obj_path.exists(), "learning_objectives.md not found"
    text = obj_path.read_text()
    assert "Plan A" in text
    assert "Plan B" in text
    assert "Plan C" in text
    assert "Plan D" in text
    assert "four plans" in text.lower()


def test_every_notebook_has_assessments():
    """Every notebook has at least one assessment cell (quiz/predict/reflect/order)."""
    assessment_pattern = re.compile(r"(quiz|predict_choice|reflect|order)\s*\(")
    for nb_path in ALL_NOTEBOOKS:
        nb = nbformat.read(str(nb_path), as_version=4)
        has_assessment = False
        for cell in nb.cells:
            if cell.cell_type == "code":
                src = "".join(cell.source)
                if assessment_pattern.search(src) and "LearningTracker" not in src:
                    has_assessment = True
                    break
        assert has_assessment, f"{nb_path} has no assessment cells"
