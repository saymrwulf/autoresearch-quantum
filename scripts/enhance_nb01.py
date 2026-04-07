"""Inject widget-based teaching cells into Plan A — Notebook 01."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_a/01_encoded_magic_state.ipynb")
nb = json.loads(NB_PATH.read_text())
ORIG = len(nb["cells"])


def md(source: str) -> dict:
    lines = source.strip().split("\n")
    src = [line + "\n" for line in lines[:-1]] + [lines[-1]]
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def code(source: str) -> dict:
    lines = source.strip().split("\n")
    src = [line + "\n" for line in lines[:-1]] + [lines[-1]]
    return {"cell_type": "code", "metadata": {}, "source": src, "outputs": [], "execution_count": None}


insertions: list[tuple[int, list[dict]]] = []

# ── After cell 1 (imports): tracker setup ───────────────────────────────────
insertions.append((1, [
    code("""from autoresearch_quantum.teaching import LearningTracker
from autoresearch_quantum.teaching.assess import quiz, predict_choice, reflect, order, checkpoint_summary

tracker = LearningTracker("plan_a_01")
print("Learning tracker active.")"""),
]))

# ── After cell 3 (T-state amplitudes): MCQ on phase ────────────────────────
insertions.append((3, [
    code("""quiz(tracker, "q1_tstate_phase",
    question="What is the phase angle of the |1\\u27E9 coefficient in the T-state?",
    options=[
        "\\u03C0/2 (90 degrees)",
        "\\u03C0/4 (45 degrees)",
        "\\u03C0/8 (22.5 degrees)",
        "\\u03C0 (180 degrees)",
    ],
    correct=1,
    section="1. Single-qubit T-state",
    bloom="remember",
    explanation=(
        "The T-state is \\\\((|0\\\\rangle + e^{i\\\\pi/4}|1\\\\rangle)/\\\\sqrt{2}\\\\). "
        "The phase \\\\(\\\\pi/4 = 45\\u00b0\\\\) is what makes it a T-gate resource."
    ))"""),
]))

# ── After cell 4 (Bloch sphere): predict expectations ──────────────────────
insertions.append((4, [
    code("""predict_choice(tracker, "q2_bloch_expectations",
    question="The T-state Bloch vector points somewhere specific. What are its X, Y, Z expectations?",
    options=[
        "\\u27E8X\\u27E9 = 1, \\u27E8Y\\u27E9 = 0, \\u27E8Z\\u27E9 = 0",
        "\\u27E8X\\u27E9 \\u2248 0.71, \\u27E8Y\\u27E9 \\u2248 0.71, \\u27E8Z\\u27E9 = 0",
        "\\u27E8X\\u27E9 = 0, \\u27E8Y\\u27E9 = 0, \\u27E8Z\\u27E9 = 1",
        "\\u27E8X\\u27E9 = 0.5, \\u27E8Y\\u27E9 = 0.5, \\u27E8Z\\u27E9 = 0.5",
    ],
    correct=1,
    section="1. Single-qubit T-state",
    bloom="understand",
    explanation=(
        "The T-state sits on the X-Y equator of the Bloch sphere at 45\\u00b0 between X and Y. "
        "Both \\u27E8X\\u27E9 and \\u27E8Y\\u27E9 equal 1/\\u221A2 \\u2248 0.707, and \\u27E8Z\\u27E9 = 0."
    ))"""),
]))

# ── After cell 5 (key insight): MCQ why T-state matters ────────────────────
insertions.append((5, [
    code("""quiz(tracker, "q3_why_tstate",
    question="Why is the T-state essential for universal fault-tolerant quantum computing?",
    options=[
        "It has the highest fidelity of all qubit states",
        "It is the only state that cannot be cloned",
        "Clifford gates alone are classically simulable; the T-state adds the missing non-Clifford resource",
        "It is the easiest state to prepare on hardware",
    ],
    correct=2,
    bloom="understand",
    explanation=(
        "The Gottesman-Knill theorem: Clifford circuits can be simulated classically. "
        "You need a non-Clifford resource (like the T-state) for quantum advantage."
    ))

checkpoint_summary(tracker, "1. Single-qubit T-state")"""),
]))

# ── After cell 7 (seed fidelities): global phase ───────────────────────────
insertions.append((7, [
    code("""quiz(tracker, "q4_global_phase",
    question="The three seed styles have different amplitudes but fidelity = 1.0. Why?",
    options=[
        "Floating-point rounding errors",
        "A global phase factor multiplies all amplitudes but has no observable consequence",
        "The Bloch sphere only shows approximate positions",
    ],
    correct=1,
    section="2. Seed styles",
    bloom="understand",
    explanation=(
        "A global phase has no physical effect. All measurements give identical probabilities. "
        "Only relative phases between basis states matter in quantum mechanics."
    ))

checkpoint_summary(tracker, "2. Seed styles")"""),
]))

# ── After cell 10 (why encode): distance MCQ ───────────────────────────────
insertions.append((10, [
    code("""quiz(tracker, "q5_distance_2",
    question='What does "distance 2" mean for a quantum error-correcting code?',
    options=[
        "It can correct any 2-qubit error",
        "It can detect any single-qubit error (but not correct it)",
        "It uses 2 ancilla qubits",
    ],
    correct=1,
    section="3. Why encode",
    bloom="remember",
    explanation=(
        "Distance d means the code can detect up to d\\u22121 errors. "
        "Distance 2 detects single-qubit errors. "
        "To correct errors you need distance \\u2265 3."
    ))"""),
]))

# ── After cell 13 (encoder explanation): gate count ─────────────────────────
insertions.append((13, [
    code("""quiz(tracker, "q6_gate_count",
    question="How many 2-qubit (CNOT) gates are in the cx_chain encoder above?",
    options=["3", "4", "5", "6"],
    correct=2,
    section="4. Encoder circuit",
    bloom="apply",
    explanation=(
        "CX(0,2), CX(1,0), CX(3,0), CX(3,1), CX(3,2) = 5 CNOT gates. "
        "Two-qubit gate count is the key cost metric on real hardware."
    ))"""),
]))

# ── After cell 15 (full prep circuit): predict amplitudes ───────────────────
insertions.append((15, [
    code("""predict_choice(tracker, "q7_nonzero_amplitudes",
    question="The encoded state has 2\\u2074 = 16 possible basis states. How many have non-zero amplitude?",
    options=["2", "4", "8", "16"],
    correct=1,
    section="5. Encoded state",
    bloom="understand",
    explanation=(
        "The [[4,2,2]] code has 4 codewords. "
        "The T-state populates all four because it is a superposition of both logical basis states, "
        "each mapping to 2 physical basis states."
    ))"""),
]))

# ── After cell 19 (stabilizer check): predict Z error effect ───────────────
insertions.append((19, [
    code("""quiz(tracker, "q8_z_error_xxxx",
    question="If we apply a Z error to qubit 0, what happens to \\u27E8XXXX\\u27E9?",
    options=[
        "Stays at +1 (no effect)",
        "Flips to \\u22121 (error detected)",
        "Becomes 0 (uncertain)",
    ],
    correct=1,
    section="6. Stabilizer verification",
    bloom="apply",
    explanation=(
        "Z anti-commutes with X: ZX = \\u2212XZ. "
        "Conjugating XXXX by Z\\u2080 flips the sign, so the expectation goes from +1 to \\u22121. "
        "This is exactly how Z errors are detected by the X-stabilizer."
    ))"""),
]))

# ── After cell 22 (X error demo): predict Y error ──────────────────────────
insertions.append((22, [
    code("""predict_choice(tracker, "q9_y_error",
    question="A Y error on qubit 2: how many stabilizers will detect it?",
    options=[
        "0 (undetected)",
        "1 (either XXXX or ZZZZ, not both)",
        "2 (both XXXX and ZZZZ)",
    ],
    correct=2,
    section="7. Error detection",
    bloom="understand",
    explanation=(
        "Y = iXZ, so it anti-commutes with both XXXX (Z part) and ZZZZ (X part). "
        "Both stabilizers flip to \\u22121. Y errors produce the most distinctive syndrome."
    ))"""),
]))

# ── After cell 24 (error table): sort error types ──────────────────────────
insertions.append((24, [
    code("""order(tracker, "q10_error_ranking",
    instruction="Sort error types by number of stabilizers they trigger (fewest first):",
    items=["X", "Z", "Y"],
    correct_order=["X", "Z", "Y"],
    bloom="analyze",
    explanation=(
        "X \\u2192 1 stabilizer (ZZZZ). Z \\u2192 1 stabilizer (XXXX). Y \\u2192 2 stabilizers (both). "
        "X and Z are tied at 1 each; Y is the most detectable."
    ))

checkpoint_summary(tracker, "7. Error detection")"""),
]))

# ── After cell 28 (encoder comparison): evaluate trade-offs ────────────────
insertions.append((28, [
    code("""reflect(tracker, "q11_encoder_tradeoff",
    question="cx_chain has depth 7, cz_compiled has depth 11. When might you prefer the deeper circuit?",
    section="8. Encoder comparison",
    bloom="evaluate",
    model_answer=(
        "If the hardware natively supports CZ gates, cx_chain would need each CNOT decomposed "
        "into CZ+H, potentially making it deeper after transpilation. "
        "The lesson: depth AFTER transpilation to the native gate set is what matters, not depth before."
    ))"""),
]))

# ── After cell 31 (acceptance circuit): ancilla purpose ─────────────────────
insertions.append((31, [
    code("""quiz(tracker, "q12_ancilla_purpose",
    question="Why do we need ancilla qubits instead of directly measuring the data qubits?",
    options=[
        "We can measure directly, but ancillas make it faster",
        "Direct measurement would collapse the data qubits, destroying the encoded state",
        "The ZZZZ operator does not exist as a physical measurement",
    ],
    correct=1,
    section="9. Verification circuits",
    bloom="understand",
    explanation=(
        "Measuring individual qubits would collapse the superposition and destroy the encoded state. "
        "Ancilla-based syndrome extraction measures the stabilizer eigenvalue without "
        "revealing the logical information."
    ))"""),
]))

# ── After cell 35 (ideal sim counts): acceptance rate ──────────────────────
insertions.append((35, [
    code("""quiz(tracker, "q13_ideal_acceptance",
    question="In the ideal (noiseless) simulation, what percentage of shots pass the syndrome check?",
    options=["About 50%", "About 75%", "100%", "It depends on the circuit"],
    correct=2,
    section="10. Ideal simulation",
    bloom="understand",
    explanation=(
        "With no noise, the state is always in the codespace, "
        "so both stabilizers always return +1 (syndrome 00). Acceptance = 100%."
    ))"""),
]))

# ── After cell 39 (postselection): trade-off ───────────────────────────────
insertions.append((39, [
    code("""quiz(tracker, "q14_postselection_tradeoff",
    question="What is the fundamental cost of postselection?",
    options=[
        "It makes the circuit deeper",
        "It reduces the number of usable shots (you pay in acceptance rate)",
        "It introduces additional errors from the ancilla measurements",
    ],
    correct=1,
    section="11. Postselection",
    bloom="understand",
    explanation=(
        "Postselection improves quality (only clean shots survive) but reduces quantity "
        "(you discard error shots). If acceptance drops too low, you need exponentially more shots."
    ))

checkpoint_summary(tracker, "11. Postselection")"""),
]))

# ── After cell 40 (summary): final dashboard ───────────────────────────────
insertions.append((40, [
    md("""---
## Final Assessment"""),
    code("""tracker.dashboard()
path = tracker.save()
print(f"Progress saved to: {path}")"""),
]))

# ── Apply insertions ───────────────────────────────────────────────────────
for after_idx, cells in reversed(insertions):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced notebook 01: {ORIG} -> {len(nb['cells'])} cells")
