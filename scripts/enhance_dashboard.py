"""Widget-based teaching cells for Plan C — Dashboard."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_c/00_dashboard.ipynb")
nb = json.loads(NB_PATH.read_text())
ORIG = len(nb["cells"])

def md(s):
    lines = s.strip().split("\n")
    return {"cell_type": "markdown", "metadata": {}, "source": [ln + "\n" for ln in lines[:-1]] + [lines[-1]]}
def code(s):
    lines = s.strip().split("\n")
    return {"cell_type": "code", "metadata": {}, "source": [ln + "\n" for ln in lines[:-1]] + [lines[-1]], "outputs": [], "execution_count": None}

ins = []

ins.append((1, [code("""from autoresearch_quantum.teaching import LearningTracker
from autoresearch_quantum.teaching.assess import quiz, predict_choice, reflect, checkpoint_summary
tracker = LearningTracker("plan_c_dashboard")
print("Learning tracker active.")""")]))

ins.append((3, [
    code("""quiz(tracker, "q1_baseline",
    question="Why does the dashboard start from a rung-1 config as baseline?",
    options=[
        "It is the only config that exists",
        "It provides sensible defaults that widgets then override one at a time",
        "Higher rungs require IBM hardware access",
    ],
    correct=1, section="1. Setup", bloom="understand",
    explanation="The rung-1 config defines the full parameter space and bootstrap incumbent. Widgets let you explore variations.")"""),
]))

ins.append((5, [
    code("""predict_choice(tracker, "q2_verification_effect",
    question="What happens to acceptance rate if you set verification to 'none'?",
    options=[
        "Acceptance rate drops because there are no checks",
        "Acceptance rate goes to 100% because no shots are filtered",
        "No change \\u2014 verification doesn't affect acceptance",
    ],
    correct=1, section="2. Exploration", bloom="apply",
    explanation="With verification='none', there are no syndrome checks, so ALL shots are accepted (100%). But quality may be lower.")"""),
    code("""reflect(tracker, "q3_tradeoff",
    question="After trying several parameter combinations, what tension do you notice between quality and acceptance?",
    section="2. Exploration", bloom="analyze",
    model_answer="Stricter verification improves quality by filtering errors, but reduces acceptance rate. The score balances this: score = quality \\u00d7 acceptance / cost.")
checkpoint_summary(tracker, "2. Exploration")"""),
]))

ins.append((ORIG - 1, [
    md("---\n## Learning Dashboard"),
    code("""tracker.dashboard()
path = tracker.save()
print(f"\\nProgress saved to: {path}")"""),
]))

for after_idx, cells in reversed(ins):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced dashboard: {ORIG} -> {len(nb['cells'])} cells")
