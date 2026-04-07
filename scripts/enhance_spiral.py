"""Widget-based teaching cells for Plan B — Spiral Notebook."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_b/spiral_notebook.ipynb")
nb = json.loads(NB_PATH.read_text())
ORIG = len(nb["cells"])

def md(s):
    lines = s.strip().split("\n")
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines[:-1]] + [lines[-1]]}
def code(s):
    lines = s.strip().split("\n")
    return {"cell_type": "code", "metadata": {}, "source": [l + "\n" for l in lines[:-1]] + [lines[-1]], "outputs": [], "execution_count": None}

ins = []

# After cell 2 (imports): tracker
ins.append((2, [code("""from autoresearch_quantum.teaching import LearningTracker
from autoresearch_quantum.teaching.assess import quiz, predict_choice, reflect, order, checkpoint_summary
tracker = LearningTracker("plan_b_spiral")
print("Learning tracker active.")""")]))

# PASS 1: remember + understand

# After cell 8 (key numbers): what is a score
ins.append((8, [
    code("""quiz(tracker, "p1_q1_what_is_score",
    question="The winning margin tells you how much the winner improved. What does a margin of 0.0 mean?",
    options=[
        "The experiment failed",
        "No challenger beat the incumbent \\u2014 the incumbent stayed",
        "All challengers tied exactly",
    ],
    correct=1, section="Pass 1: Demo", bloom="remember",
    explanation="Margin 0.0 means the incumbent was not replaced. The ratchet guarantee: never worse.")"""),
]))

# After cell 14 (score landscape chart): predict
ins.append((14, [
    code("""predict_choice(tracker, "p1_q2_score_spread",
    question="Looking at the score landscape: is there a large spread between the best and worst experiments?",
    options=[
        "No \\u2014 all experiments score roughly the same",
        "Yes \\u2014 there is significant variation, meaning parameter choice matters a lot",
        "Impossible to tell from a bar chart",
    ],
    correct=1, section="Pass 1: Demo", bloom="understand",
    explanation="Parameter choice strongly affects the score. This is why optimization matters.")

checkpoint_summary(tracker, "Pass 1: Demo")"""),
]))

# PASS 2: apply + analyze

# After cell 18 (T-state Bloch): T-state phase
ins.append((18, [
    code("""quiz(tracker, "p2_q1_tstate",
    question="The T-state amplitude on |1\\u27E9 has a specific phase. What is it?",
    options=["\\u03C0/2 (90\\u00b0)", "\\u03C0/4 (45\\u00b0)", "\\u03C0/8 (22.5\\u00b0)"],
    correct=1, section="Pass 2: Concepts", bloom="remember",
    explanation="The phase is \\u03C0/4 = 45\\u00b0. The gate is called T (for \\u03C0/8) because of Bloch sphere conventions.")"""),
]))

# After cell 24 (stabilizer check): what +1 means
ins.append((24, [
    code("""quiz(tracker, "p2_q2_stabilizer",
    question="Both stabilizer expectations are +1. What does this confirm?",
    options=[
        "The state has high energy",
        "The state is in the [[4,2,2]] codespace \\u2014 no errors detected",
        "All qubits are in |0\\u27E9",
    ],
    correct=1, section="Pass 2: Concepts", bloom="understand",
    explanation="Stabilizer eigenvalue +1 is the codespace condition. Any single-qubit error would flip at least one to \\u22121.")"""),
]))

# After cell 30 (postselection): what postselection costs
ins.append((30, [
    code("""quiz(tracker, "p2_q3_postselection",
    question="Postselection improves quality by discarding error-flagged shots. What is the cost?",
    options=[
        "It makes the circuit deeper",
        "You lose shots \\u2014 fewer usable data points",
        "It introduces new types of errors",
    ],
    correct=1, section="Pass 2: Concepts", bloom="understand",
    explanation="Postselection trades quantity for quality. Fewer usable shots means worse statistics or more total shots needed.")"""),
]))

# After cell 38 (cost): cost vs quality tension
ins.append((38, [
    code("""predict_choice(tracker, "p2_q4_cost_quality",
    question="More complex circuits might give better quality but higher cost. What does the score formula do with this tension?",
    options=[
        "Ignores cost entirely \\u2014 only quality matters",
        "Divides quality by cost, so you need quality to outweigh the cost",
        "Picks the cheapest circuit regardless of quality",
    ],
    correct=1, section="Pass 2: Scoring", bloom="apply",
    explanation="score = quality \\u00d7 acceptance / cost. A circuit that is 2x better but 3x more expensive scores worse.")

checkpoint_summary(tracker, "Pass 2: Scoring")"""),
]))

# After cell 44 (challengers): how neighbors work
ins.append((44, [
    code("""quiz(tracker, "p2_q5_neighbors",
    question="Each NeighborWalk challenger differs from the incumbent in how many parameters?",
    options=["0", "1", "2", "All of them"],
    correct=1, section="Pass 2: Ratchet", bloom="apply",
    explanation="NeighborWalk changes exactly one parameter at a time. This is systematic but cannot find parameter interactions.")

checkpoint_summary(tracker, "Pass 2: Ratchet")"""),
]))

# PASS 3: evaluate + create

# After cell 59 (scoring comparison): reflect
ins.append((59, [
    code("""reflect(tracker, "p3_q1_scoring_choice",
    question="You see that different scoring functions rank experiments differently. When would you choose factory throughput over WAC?",
    section="Pass 3: Scoring", bloom="evaluate",
    model_answer="Factory throughput penalizes cost more heavily. Use it when you are producing many T-states in a pipeline and throughput matters more than per-state quality.")"""),
]))

# After cell 67 (strategies head-to-head): compare
ins.append((67, [
    code("""order(tracker, "p3_q2_strategy_comparison",
    instruction="Rank strategies by ability to find multi-parameter interactions (worst to best):",
    items=["NeighborWalk", "RandomCombo", "LessonGuided"],
    correct_order=["NeighborWalk", "LessonGuided", "RandomCombo"],
    section="Pass 3: Strategies", bloom="analyze",
    explanation="NeighborWalk: 1 axis only. LessonGuided: focused by rules. RandomCombo: multiple axes, can find synergies.")"""),
]))

# After cell 75 (transfer): evaluate
ins.append((75, [
    code("""quiz(tracker, "p3_q3_transfer",
    question="A spec scores 0.8 on fake_brisbane but 0.3 on a different backend. What does this tell you?",
    options=[
        "The spec is bad",
        "The spec is overfitted to fake_brisbane's specific noise profile",
        "The other backend is broken",
    ],
    correct=1, section="Pass 3: Transfer", bloom="evaluate",
    explanation="A large score drop on transfer means the settings were tuned to one backend's quirks rather than being generally good.")

checkpoint_summary(tracker, "Pass 3: Transfer")"""),
]))

# After cell 80 (summary): dashboard
ins.append((80, [
    md("---\n## Final Assessment"),
    code("""tracker.dashboard()
path = tracker.save()
print(f"\\nProgress saved to: {path}")"""),
]))

for after_idx, cells in reversed(ins):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced spiral: {ORIG} -> {len(nb['cells'])} cells")
