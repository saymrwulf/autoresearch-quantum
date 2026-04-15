"""Widget-based teaching cells for Plan C — Track C: Search."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_c/track_c_search.ipynb")
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
tracker = LearningTracker("plan_c_track_c")
print("Learning tracker active.")""")]))

# After cell 3 (parameter space)
ins.append((3, [
    code("""quiz(tracker, "q1_why_search",
    question="The parameter space is finite. Why not just try every combination?",
    options=[
        "The space is infinite",
        "Each evaluation costs time/compute; smart search finds good solutions faster",
        "Exhaustive search always finds worse solutions",
    ],
    correct=1, section="1. Parameter space", bloom="understand",
    explanation="Each evaluation requires noisy simulation (or hardware QPU time). Smart search finds good solutions in fewer evaluations.")"""),
]))

# After cell 5 (bootstrap incumbent)
ins.append((5, [
    code("""quiz(tracker, "q2_incumbent",
    question="What is the bootstrap incumbent?",
    options=[
        "A randomly chosen starting point",
        "A hand-picked reasonable default that the ratchet tries to beat",
        "The theoretically optimal configuration",
    ],
    correct=1, section="2. Incumbent", bloom="remember",
    explanation="The bootstrap incumbent is a domain-expert guess. The ratchet guarantee: it never gets worse from here.")
checkpoint_summary(tracker, "2. Incumbent")"""),
]))

# After cell 7 (NeighborWalk)
ins.append((7, [
    code("""quiz(tracker, "q3_neighborwalk",
    question="NeighborWalk changes how many parameters per challenger?",
    options=["0", "Exactly 1", "Up to 3", "All of them"],
    correct=1, section="3. NeighborWalk", bloom="understand",
    explanation="One parameter at a time, trying all alternative values. Systematic but blind to parameter interactions.")"""),
]))

# After cell 9 (RandomCombo)
ins.append((9, [
    code("""order(tracker, "q4_strategy_interactions",
    instruction="Rank strategies by ability to find multi-parameter interactions (worst to best):",
    items=["NeighborWalk", "RandomCombo"],
    correct_order=["NeighborWalk", "RandomCombo"],
    section="4. RandomCombo", bloom="analyze",
    explanation="NeighborWalk: 1 axis only, cannot find interactions. RandomCombo mutates multiple axes simultaneously.")
checkpoint_summary(tracker, "4. RandomCombo")"""),
]))

# After cell 14 (ratchet step)
ins.append((14, [
    code("""quiz(tracker, "q5_no_winner",
    question="What happens if no challenger beats the incumbent?",
    options=[
        "The harness picks the best challenger anyway",
        "The incumbent stays; the step is logged with zero improvement",
        "The harness doubles the number of challengers",
    ],
    correct=1, section="6. Ratchet step", bloom="understand",
    explanation="Ratchet guarantee: the incumbent never gets worse. No-improvement steps are still valuable data for lesson extraction.")"""),
]))

# After cell 16 (full rung)
ins.append((16, [
    code("""quiz(tracker, "q6_patience",
    question="Patience=2 means the rung stops after 2 consecutive steps with no improvement. Why?",
    options=[
        "To save memory",
        "If 2 rounds of challengers all lose, the nearby parameter space is likely exhausted",
        "2 is always the optimal patience value",
    ],
    correct=1, section="7. Full rung", bloom="evaluate",
    explanation="Patience prevents wasting compute once the search has converged. The budget is better spent on the next rung.")
checkpoint_summary(tracker, "7. Full rung")"""),
]))

# After cell 19 (lesson narrative)
ins.append((19, [
    code("""reflect(tracker, "q7_lesson_quality",
    question="Read the lesson narrative. What actionable insight does it give? What would make it better?",
    section="8. Lessons", bloom="evaluate",
    model_answer="A good lesson names specific values that helped/hurt and explains WHY. Machine-readable SearchRules are often more actionable than the narrative.")"""),
]))

# After cell 20 (machine rules)
ins.append((20, [
    code("""quiz(tracker, "q8_fix_vs_avoid",
    question="'fix' vs 'avoid' rules: what's the difference?",
    options=[
        "'fix' locks a value permanently; 'avoid' removes a value from the search space",
        "'fix' repairs a bug; 'avoid' prevents a crash",
        "They are synonyms",
    ],
    correct=0, section="8. Lessons", bloom="remember",
    explanation="'fix': always use this value. 'avoid': never use this value. Both narrow the search space for future rungs.")
checkpoint_summary(tracker, "8. Lessons")"""),
]))

# After cell 24 (narrowing)
ins.append((24, [
    code("""quiz(tracker, "q9_narrowing",
    question="What does search space narrowing accomplish?",
    options=[
        "It removes entire parameter dimensions",
        "It removes poorly-performing values, keeping the dimension with fewer options",
        "It adds new parameter values",
    ],
    correct=1, section="10. Narrowing", bloom="understand",
    explanation="Narrowing prunes bad values based on evidence. The dimension stays but with fewer options. A minimum is preserved to prevent overfitting.")"""),
]))

# After cell 28 (transfer evaluation)
ins.append((28, [
    code("""quiz(tracker, "q10_transfer",
    question="A spec scores 0.8 on one backend but 0.3 on another. What does this mean?",
    options=[
        "The spec is bad overall",
        "The spec is overfitted to the first backend's noise profile",
        "The second backend is broken",
    ],
    correct=1, section="12. Transfer", bloom="evaluate",
    explanation="A large transfer drop means settings are tuned to one backend's quirks. The ratchet tests transfer to find robust, generalizable configurations.")
checkpoint_summary(tracker, "12. Transfer")"""),
]))

# After last cell: dashboard
ins.append((ORIG - 1, [
    md("---\n## Final Assessment"),
    code("""tracker.dashboard()
path = tracker.save()
print(f"\\nProgress saved to: {path}")"""),
]))

for after_idx, cells in reversed(ins):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced Track C: {ORIG} -> {len(nb['cells'])} cells")
