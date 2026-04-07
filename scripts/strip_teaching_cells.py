"""Remove all teaching-injected cells from notebooks, restoring original content."""
import json
from pathlib import Path

NOTEBOOKS = [
    "notebooks/plan_a/01_encoded_magic_state.ipynb",
    "notebooks/plan_a/02_measuring_progress.ipynb",
    "notebooks/plan_a/03_the_ratchet.ipynb",
    "notebooks/plan_b/spiral_notebook.ipynb",
    "notebooks/plan_c/00_dashboard.ipynb",
    "notebooks/plan_c/track_a_physics.ipynb",
    "notebooks/plan_c/track_b_engineering.ipynb",
    "notebooks/plan_c/track_c_search.ipynb",
]

TEACHING_MARKERS = [
    "LearningTracker",
    "tracker.set_section",
    "multiple_choice(",
    "predict(",
    "check_prediction(",
    "numerical_answer(",
    "free_response(",
    "code_challenge(",
    "concept_sort(",
    "checkpoint_summary(",
    "tracker.dashboard()",
    "tracker.save()",
    "## Final Assessment",
    "Check your understanding",
    "Prediction",
    "Exploration Guide",
    "Learning Dashboard",
]

for nb_path_str in NOTEBOOKS:
    nb_path = Path(nb_path_str)
    if not nb_path.exists():
        continue

    nb = json.loads(nb_path.read_text())
    original_count = len(nb["cells"])

    kept = []
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        is_teaching = any(marker in src for marker in TEACHING_MARKERS)
        if not is_teaching:
            kept.append(cell)

    nb["cells"] = kept
    nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
    print(f"{nb_path}: {original_count} -> {len(kept)} cells")
