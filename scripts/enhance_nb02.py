"""Widget-based teaching cells for Plan A — Notebook 02: Measuring Progress."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_a/02_measuring_progress.ipynb")
nb = json.loads(NB_PATH.read_text())
ORIG = len(nb["cells"])

def md(s):
    lines = s.strip().split("\n")
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines[:-1]] + [lines[-1]]}

def code(s):
    lines = s.strip().split("\n")
    return {"cell_type": "code", "metadata": {}, "source": [l + "\n" for l in lines[:-1]] + [lines[-1]], "outputs": [], "execution_count": None}

ins = []

# After cell 1 (imports): tracker
ins.append((1, [code("""from autoresearch_quantum.teaching import LearningTracker
from autoresearch_quantum.teaching.assess import quiz, predict_choice, reflect, order, checkpoint_summary
tracker = LearningTracker("plan_a_02")
print("Learning tracker active.")""")]))

# After cell 3 (ideal state recap)
ins.append((3, [
    md("""### Recap check\n\nBefore we add noise, make sure the Notebook 1 concepts are solid."""),
    code("""quiz(tracker, "q1_stabilizer_eigenvalue",
    question="What do the stabilizer eigenvalues tell us about a quantum state?",
    options=[
        "They measure the energy of the system",
        "Eigenvalue +1 means the state is in the codespace (no error detected)",
        "They tell us which logical qubit is |0\\u27E9 vs |1\\u27E9",
        "They count the number of entangled qubits",
    ],
    correct=1,
    section="1. Recap",
    bloom="remember",
    explanation=(
        "Stabilizer eigenvalue +1 means the state satisfies the code constraints. "
        "If any single-qubit error occurs, at least one stabilizer flips to \\u22121."
    ))"""),
]))

# After cell 5 (noisy backend)
ins.append((5, [
    md("""### What does noise do?\n\nThe fake_brisbane backend simulates realistic noise from IBM's 127-qubit Eagle processor. Gate errors, readout errors, and crosstalk all contribute."""),
    code("""predict_choice(tracker, "q2_noise_effect",
    question="When we run the same circuit with noise, what happens to the syndrome distribution?",
    options=[
        "Syndrome is still always '00' \\u2014 noise is too small to matter",
        "Some shots will have non-zero syndrome \\u2014 noise causes detectable errors",
        "All shots will have non-zero syndrome \\u2014 noise is overwhelming",
    ],
    correct=1,
    section="2. Adding noise",
    bloom="understand",
    explanation=(
        "Realistic noise causes some fraction of shots to leave the codespace, "
        "producing non-zero syndromes. Typical acceptance rates are 40\\u201380% for current hardware."
    ))"""),
]))

# After cell 9 (postselection results)
ins.append((9, [
    code("""quiz(tracker, "q3_acceptance_cost",
    question="If the acceptance rate is 50%, what does that mean for the experiment?",
    options=[
        "Half the qubits failed",
        "Half the shots were discarded \\u2014 we need 2x shots for the same statistics",
        "The circuit has 50% fidelity",
        "The code corrected half the errors",
    ],
    correct=1,
    section="3. Postselection",
    bloom="understand",
    explanation=(
        "Acceptance rate = fraction of shots surviving postselection. "
        "At 50%, you need twice as many total shots. This is a direct cost."
    ))
checkpoint_summary(tracker, "3. Postselection")"""),
]))

# After cell 11 (witness circuits)
ins.append((11, [
    code("""quiz(tracker, "q4_three_circuits",
    question="Why does the experiment use 3 separate circuits instead of measuring all operators at once?",
    options=[
        "The operators don't commute, so measuring one disturbs the others",
        "It's a software limitation",
        "Each operator requires different ancilla qubits",
    ],
    correct=0,
    section="4. Logical operators",
    bloom="analyze",
    explanation=(
        "Logical X and Logical Y do not commute. Measuring one collapses the state "
        "into an eigenstate that invalidates the other measurement."
    ))"""),
]))

# After cell 13 (witness value)
ins.append((13, [
    md("""### The magic witness formula\n\n$$W = \\frac{1 + (\\langle X_L \\rangle + \\langle Y_L \\rangle)/\\sqrt{2}}{2} \\times \\frac{1 + \\langle Z_{\\text{spectator}} \\rangle}{2}$$\n\nFor a perfect T-state: $\\langle X_L \\rangle = \\langle Y_L \\rangle = 1/\\sqrt{2}$ and $\\langle Z_{\\text{spec}} \\rangle = 1$, giving $W = 1.0$."""),
    code("""quiz(tracker, "q5_ideal_witness",
    question="For a perfect (noiseless) T-state, what is the magic witness value?",
    options=["0.0", "0.5", "1/\\u221A2 \\u2248 0.707", "1.0"],
    correct=3,
    section="5. Witness formula",
    bloom="apply",
    explanation=(
        "magic_factor = (1 + (1/\\u221A2 + 1/\\u221A2)/\\u221A2) / 2 = (1+1)/2 = 1. "
        "spectator_factor = (1+1)/2 = 1. Product = 1.0."
    ))
checkpoint_summary(tracker, "5. Witness formula")"""),
]))

# After cell 15 (fidelity)
ins.append((15, [
    code("""quiz(tracker, "q6_witness_vs_fidelity",
    question="The witness and fidelity both measure quality. How do they differ?",
    options=[
        "They are the same thing",
        "Fidelity measures overlap with the ideal state; the witness tests magic-state properties specifically",
        "Fidelity is always higher than the witness",
    ],
    correct=1,
    section="6. Fidelity",
    bloom="analyze",
    explanation=(
        "Fidelity captures total overlap with the ideal state. "
        "The witness specifically tests the T-state signature. "
        "A state can have moderate fidelity but low witness if the noise corrupts the magic structure."
    ))"""),
]))

# After cell 17 (scoring)
ins.append((17, [
    md("""### The scoring formula\n\n$$\\text{score} = \\frac{\\text{quality} \\times \\text{acceptance\\_rate}}{\\text{cost}}$$"""),
    code("""predict_choice(tracker, "q7_score_tension",
    question="If you add stricter verification, what happens to the score?",
    options=[
        "Score always increases \\u2014 more checks = better quality",
        "Score always decreases \\u2014 more checks = lower acceptance",
        "It depends \\u2014 quality improves but acceptance drops; the net effect depends on noise",
    ],
    correct=2,
    section="7. Scoring",
    bloom="evaluate",
    explanation=(
        "Stricter verification filters more errors (higher quality) but rejects more shots (lower acceptance). "
        "At low noise, quality gain dominates. At high noise, acceptance crashes."
    ))
checkpoint_summary(tracker, "7. Scoring")"""),
]))

# After cell 20 (sweep chart)
ins.append((20, [
    code("""reflect(tracker, "q8_sweep_insight",
    question="Looking at the parameter sweep charts, which optimization level gives the best score and why?",
    section="8. Parameter sweep",
    bloom="evaluate",
    model_answer=(
        "The best optimization level balances gate count reduction against qubit routing overhead. "
        "Level 2 or 3 often wins because aggressive optimization reduces noisy 2-qubit gates. "
        "But the best choice depends on the specific backend topology."
    ))"""),
]))

# After cell 22 (failure modes)
ins.append((22, [
    code("""order(tracker, "q9_failure_ordering",
    instruction="Rank failure modes from least to most severe for magic state quality:",
    items=["high_cost_low_throughput", "poor_acceptance_rate", "low_magic_witness"],
    correct_order=["high_cost_low_throughput", "poor_acceptance_rate", "low_magic_witness"],
    section="9. Failure modes",
    bloom="analyze",
    explanation=(
        "High cost is fixable (fewer gates). Poor acceptance is concerning (too many errors). "
        "Low magic witness is worst \\u2014 the state has lost its T-state character."
    ))
checkpoint_summary(tracker, "9. Failure modes")"""),
]))

# After cell 24 (factory throughput)
ins.append((24, [
    code("""quiz(tracker, "q10_factory_vs_wac",
    question="When would factory throughput scoring beat default WAC scoring?",
    options=[
        "When raw quality matters most",
        "When producing many T-states in a pipeline and throughput matters more than per-state quality",
        "When running on hardware instead of a simulator",
    ],
    correct=1,
    section="10. Factory throughput",
    bloom="evaluate",
    explanation=(
        "Factory throughput penalizes cost more heavily because in a pipeline, "
        "the rate of producing usable T-states matters more than any individual one."
    ))
checkpoint_summary(tracker, "10. Factory throughput")"""),
]))

# After cell 25 (final markdown): dashboard
ins.append((25, [
    md("---\n## Final Assessment"),
    code("""tracker.dashboard()
path = tracker.save()
print(f"\\nProgress saved to: {path}")"""),
]))

for after_idx, cells in reversed(ins):
    for i, cell in enumerate(cells):
        nb["cells"].insert(after_idx + 1 + i, cell)

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Enhanced notebook 02: {ORIG} -> {len(nb['cells'])} cells")
