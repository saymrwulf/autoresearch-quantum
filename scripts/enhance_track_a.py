"""Widget-based teaching cells for Plan C — Track A: Physics."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_c/track_a_physics.ipynb")
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
tracker = LearningTracker("plan_c_track_a")
print("Learning tracker active.")""")]))

# After cell 2 (Eastin-Knill intro)
ins.append((2, [
    code("""quiz(tracker, "q1_eastin_knill",
    question="The Eastin-Knill theorem limits fault-tolerant QC. What does it say?",
    options=[
        "No quantum code can detect all errors",
        "No quantum code has a universal set of transversal gates \\u2014 you need a non-transversal resource like magic states",
        "Quantum error correction always requires more physical qubits than logical qubits",
    ],
    correct=1, section="1. Why magic states", bloom="remember",
    explanation="Eastin-Knill: you cannot implement a universal gate set transversally in any code. The T-gate is the most common non-transversal resource, supplied via magic states.")"""),
]))

# After cell 4 (T-state Bloch)
ins.append((4, [
    code("""quiz(tracker, "q2_tstate_phase",
    question="The T-state phase on |1\\u27E9 is:",
    options=["\\u03C0/2", "\\u03C0/4", "\\u03C0/8"],
    correct=1, section="2. T-state", bloom="remember",
    explanation="\\u03C0/4 = 45\\u00b0. Despite the gate being called T (\\u03C0/8 rotation on the Bloch sphere), the state phase is \\u03C0/4.")"""),
]))

# After cell 7 (three preps)
ins.append((7, [
    code("""quiz(tracker, "q3_global_phase",
    question="Three gate sequences produce states with different amplitudes but fidelity 1.0. Why?",
    options=[
        "Floating-point errors",
        "Global phase has no physical consequence",
        "They actually produce different states",
    ],
    correct=1, section="3. Preparations", bloom="understand",
    explanation="A global phase multiplies ALL amplitudes. No measurement can distinguish the states.")
checkpoint_summary(tracker, "3. Preparations")"""),
]))

# After cell 9 (stabilizer properties)
ins.append((9, [
    code("""quiz(tracker, "q4_stabilizer_square",
    question="Each stabilizer squares to the identity (S\\u00b2 = I). What does this imply about its eigenvalues?",
    options=[
        "Eigenvalues can be anything",
        "Eigenvalues are exactly +1 or \\u22121",
        "Eigenvalues are 0 or 1",
    ],
    correct=1, section="4. [[4,2,2]] code", bloom="understand",
    explanation="If S\\u00b2 = I, then S has eigenvalues \\u00b11. The codespace has eigenvalue +1; error states have \\u22121.")"""),
]))

# After cell 11 (logical operators)
ins.append((11, [
    code("""quiz(tracker, "q5_logical_ops",
    question="Why does the logical Y operator (Y\\u2080Z\\u2081X\\u2082) involve 3 qubits instead of just 1?",
    options=[
        "It's a bug in the code",
        "In a quantum code, logical operators act on the encoded information which is spread across multiple physical qubits",
        "Y is always a 3-qubit operator",
    ],
    correct=1, section="5. Logical operators", bloom="understand",
    explanation="The logical information is distributed across all physical qubits. Logical operators must act on this distributed encoding.")
checkpoint_summary(tracker, "5. Logical operators")"""),
]))

# After cell 16 (encoded state verification)
ins.append((16, [
    code("""predict_choice(tracker, "q6_z_error",
    question="A single Z error on qubit 0: which stabilizer detects it?",
    options=[
        "ZZZZ (Z commutes with Z, so it detects Z errors)",
        "XXXX (Z anti-commutes with X, flipping the XXXX eigenvalue)",
        "Neither \\u2014 Z errors are invisible",
    ],
    correct=1, section="8. Error detection", bloom="apply",
    explanation="Z anti-commutes with X. A Z error on any qubit flips the XXXX eigenvalue from +1 to \\u22121.")"""),
]))

# After cell 18 (error table)
ins.append((18, [
    code("""order(tracker, "q7_error_types",
    instruction="Sort error types by how many stabilizers they trigger (fewest first):",
    items=["X", "Z", "Y"],
    correct_order=["X", "Z", "Y"],
    section="8. Error detection", bloom="analyze",
    explanation="X\\u21921 (ZZZZ). Z\\u21921 (XXXX). Y\\u21922 (both). X and Z are tied.",
    ties=[["X", "Z"]])
checkpoint_summary(tracker, "8. Error detection")"""),
]))

# After cell 20 (witness formula)
ins.append((20, [
    code("""quiz(tracker, "q8_ideal_witness",
    question="For a perfect T-state, the magic witness W equals:",
    options=["0.0", "0.5", "1/\\u221A2", "1.0"],
    correct=3, section="9. Witness formula", bloom="apply",
    explanation="Ideal values give magic_factor = 1 and spectator_factor = 1. Product = 1.0.")"""),
]))

# After cell 22 (witness degradation plot)
ins.append((22, [
    code("""reflect(tracker, "q9_witness_sensitivity",
    question="The witness curve drops sharply away from the peak. Why is this useful?",
    section="10. Witness degradation", bloom="evaluate",
    model_answer="A sharp peak means the witness is sensitive to small deviations from the ideal T-state. This sensitivity is what makes it a good diagnostic: even moderate noise produces a noticeable drop.")
checkpoint_summary(tracker, "10. Witness degradation")"""),
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
print(f"Enhanced Track A: {ORIG} -> {len(nb['cells'])} cells")
