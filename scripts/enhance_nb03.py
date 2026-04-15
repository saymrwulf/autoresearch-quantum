"""Widget-based teaching cells for Plan A — Notebook 03: The Ratchet."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_a/03_the_ratchet.ipynb")
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
from autoresearch_quantum.teaching.assess import quiz, predict_choice, reflect, order, checkpoint_summary
tracker = LearningTracker("plan_a_03")
print("Learning tracker active.")""")]))

ins.append((3, [
    md("""### The ratchet guarantee\n\nThe key property: the incumbent **never gets worse**. A challenger must demonstrably beat the incumbent to replace it."""),
    code("""quiz(tracker, "q1_ratchet_guarantee",
    question="What is the ratchet guarantee?",
    options=[
        "Every step improves the score",
        "The incumbent never gets worse \\u2014 challengers must beat it to replace it",
        "The search space shrinks every step",
        "The ratchet always converges to the global optimum",
    ],
    correct=1, section="1. Incumbent-challenger", bloom="remember",
    explanation="The ratchet is monotonic: if no challenger beats the incumbent, the incumbent stays. This does NOT guarantee finding the global optimum.")"""),
]))

ins.append((5, [
    code("""quiz(tracker, "q2_neighborwalk",
    question="How does NeighborWalk generate challengers?",
    options=[
        "Changes all parameters simultaneously to random values",
        "Changes exactly one parameter at a time to each of its other possible values",
        "Applies gradient descent to continuous parameters",
    ],
    correct=1, section="2. Challengers", bloom="understand",
    explanation="NeighborWalk is single-axis: for each dimension, try every alternative value while keeping all other dimensions fixed.")
checkpoint_summary(tracker, "2. Challengers")"""),
]))

ins.append((9, [
    code("""predict_choice(tracker, "q3_challenger_wins",
    question="Looking at the bar chart: did any challenger beat the incumbent?",
    options=[
        "Yes \\u2014 at least one bar is taller than INCUMBENT",
        "No \\u2014 the incumbent bar is the tallest",
        "Can't tell from a bar chart",
    ],
    correct=0, section="3. Evaluation", bloom="apply",
    explanation="In most runs, at least one challenger finds a better configuration.")"""),
]))

ins.append((11, [
    code("""quiz(tracker, "q4_no_improvement",
    question="What happens if ALL challengers score lower than the incumbent?",
    options=[
        "The harness picks the best challenger anyway",
        "The incumbent stays and the step is logged with zero improvement",
        "The harness generates more challengers until one wins",
    ],
    correct=1, section="4. Ratchet step", bloom="understand",
    explanation="Monotonic guarantee: if no challenger wins, the incumbent stays. Consecutive no-improvement steps trigger patience.")
checkpoint_summary(tracker, "4. Ratchet step")"""),
]))

ins.append((14, [
    code("""reflect(tracker, "q5_lesson_quality",
    question="Read the lesson narrative above. What actionable insight does it give? What would make it better?",
    section="5. Lesson", bloom="evaluate",
    model_answer="A good lesson names specific parameter values that helped/hurt and explains WHY. The machine-readable rules are often more actionable than the narrative.")"""),
]))

ins.append((18, [
    md("""### Strategy comparison\n\n- **NeighborWalk**: 1 axis at a time, systematic\n- **RandomCombo**: multiple axes, random\n- **LessonGuided**: rule-biased from previous rungs"""),
    code("""order(tracker, "q6_strategy_breadth",
    instruction="Rank strategies from narrowest to broadest exploration:",
    items=["NeighborWalk", "RandomCombo", "LessonGuided"],
    correct_order=["NeighborWalk", "LessonGuided", "RandomCombo"],
    section="6. Search strategies", bloom="analyze",
    explanation="NeighborWalk: 1 param (narrowest). LessonGuided: focused by rules (medium). RandomCombo: multiple params randomly (broadest).")"""),
]))

ins.append((20, [
    code("""quiz(tracker, "q7_fix_vs_avoid",
    question="What is the difference between a 'fix' rule and an 'avoid' rule?",
    options=[
        "'fix' locks a value permanently; 'avoid' removes a value from the search space",
        "'fix' repairs a bug; 'avoid' prevents a crash",
        "They are synonyms",
    ],
    correct=0, section="7. Lesson-guided", bloom="remember",
    explanation="'fix': this value is clearly best, always use it. 'avoid': this value consistently hurts, remove it.")
checkpoint_summary(tracker, "7. Lesson-guided")"""),
]))

ins.append((23, [
    code("""quiz(tracker, "q8_propagation",
    question="Why does the ratchet propagate the winning spec to the next rung?",
    options=[
        "To save typing the spec again",
        "The winner from rung N is a good starting point for rung N+1, avoiding cold-start",
        "Each rung must use the same spec",
    ],
    correct=1, section="8. Cross-rung", bloom="understand",
    explanation="Cross-rung propagation transfers knowledge: best settings from one rung become the starting point for the next.")"""),
]))

ins.append((25, [
    code("""quiz(tracker, "q9_transfer_quality",
    question="When is a transfer score 'good'?",
    options=[
        "When it is higher than 0",
        "When it is close to the original score on the source backend",
        "When it is exactly 1.0",
    ],
    correct=1, section="9. Transfer", bloom="evaluate",
    explanation="Good transfer means settings work almost as well on the target backend. A large drop means overfitting to the source noise profile.")
checkpoint_summary(tracker, "9. Transfer")"""),
]))

ins.append((26, [
    md("---\n## Final Assessment"),
    code("""tracker.dashboard()
path = tracker.save()
print(f"\\nProgress saved to: {path}")"""),
]))

for after_idx, cells in reversed(ins):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced notebook 03: {ORIG} -> {len(nb['cells'])} cells")
