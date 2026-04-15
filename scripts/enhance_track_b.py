"""Widget-based teaching cells for Plan C — Track B: Engineering."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/plan_c/track_b_engineering.ipynb")
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
tracker = LearningTracker("plan_c_track_b")
print("Learning tracker active.")""")]))

# After cell 3 (ideal vs noisy)
ins.append((3, [
    code("""predict_choice(tracker, "q1_noise_histogram",
    question="Comparing the ideal and noisy histograms: what is the main visible difference?",
    options=[
        "The noisy histogram has fewer bars",
        "The noisy histogram spreads probability across many more bitstrings",
        "They look identical",
    ],
    correct=1, section="1. Ideal vs noisy", bloom="understand",
    explanation="Noise causes probability to leak from the valid codewords to other basis states. This spreading is the visual signature of decoherence.")"""),
]))

# After cell 5 (backend metadata)
ins.append((5, [
    code("""quiz(tracker, "q2_native_gates",
    question="The hardware has native gates like CX, SX, RZ. What happens to non-native gates like H?",
    options=[
        "They are executed directly",
        "The transpiler decomposes them into native gate sequences",
        "They cause an error",
    ],
    correct=1, section="2. Backend", bloom="understand",
    explanation="The transpiler converts all gates to the hardware's native set. H becomes SX + RZ. This decomposition adds gates and thus noise.")
checkpoint_summary(tracker, "2. Backend")"""),
]))

# After cell 7 (transpilation levels)
ins.append((7, [
    code("""predict_choice(tracker, "q3_opt_levels",
    question="Higher transpilation optimization levels reduce gate count. Is this always better?",
    options=[
        "Yes \\u2014 fewer gates always means less noise",
        "Not necessarily \\u2014 aggressive optimization may reroute qubits in ways that increase cross-talk",
        "No \\u2014 lower optimization is always more reliable",
    ],
    correct=1, section="3. Transpilation", bloom="analyze",
    explanation="Optimization involves trade-offs. Reducing gates helps, but qubit routing decisions can place operations on noisier connections.")"""),
]))

# After cell 9 (cost model)
ins.append((9, [
    code("""quiz(tracker, "q4_cost_driver",
    question="What is the dominant cost driver for most quantum circuits?",
    options=[
        "Single-qubit gate count",
        "Two-qubit (CX/CZ) gate count \\u2014 these are 10-100x noisier than single-qubit gates",
        "Classical post-processing time",
    ],
    correct=1, section="4. Cost model", bloom="apply",
    explanation="Two-qubit gates have error rates 10-100x higher than single-qubit gates on current hardware. Minimizing 2Q count is the primary optimization target.")
checkpoint_summary(tracker, "4. Cost model")"""),
]))

# After cell 11 (acceptance rates)
ins.append((11, [
    code("""quiz(tracker, "q5_acceptance_meaning",
    question="Acceptance rate of 60% means:",
    options=[
        "60% of the circuit gates succeeded",
        "60% of shots passed the stabilizer check \\u2014 40% had detectable errors",
        "The state has 60% fidelity",
    ],
    correct=1, section="5. Acceptance", bloom="apply",
    explanation="40% of shots triggered a syndrome flag and were discarded. You need ~1.7x the shots to get the same number of clean data points.")
checkpoint_summary(tracker, "5. Acceptance")"""),
]))

# After cell 16 (failure modes)
ins.append((16, [
    code("""order(tracker, "q6_failure_severity",
    instruction="Rank failure modes from least to most severe:",
    items=["high_cost", "poor_acceptance", "low_magic_witness"],
    correct_order=["high_cost", "poor_acceptance", "low_magic_witness"],
    section="7. Failure modes", bloom="analyze",
    explanation="High cost is fixable (optimize gates). Poor acceptance wastes shots. Low witness means the T-state character is lost \\u2014 the experiment's purpose has failed.")
checkpoint_summary(tracker, "7. Failure modes")"""),
]))

# After cell 18 (scoring formula)
ins.append((18, [
    code("""reflect(tracker, "q7_score_manual",
    question="You see the score computed manually from quality, acceptance, and cost. Which component dominates and why?",
    section="8. Scoring", bloom="evaluate",
    model_answer="It depends on the noise regime. At low noise: cost dominates (quality and acceptance are both near 1). At high noise: acceptance dominates (many shots rejected). The score formula surfaces whichever factor is the bottleneck.")"""),
]))

# After cell 20 (factory scoring)
ins.append((20, [
    code("""quiz(tracker, "q8_factory_vs_wac",
    question="Two scorers rank experiments differently. What determines which to use?",
    options=[
        "Always use WAC \\u2014 it's the default",
        "Your operational goal: quality per state (WAC) vs production rate (factory throughput)",
        "Use factory throughput only on real hardware",
    ],
    correct=1, section="9. Factory throughput", bloom="evaluate",
    explanation="The choice of scorer encodes your priorities. WAC optimizes per-state quality. Factory throughput optimizes for a T-state production pipeline.")
checkpoint_summary(tracker, "9. Factory throughput")"""),
]))

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
print(f"Enhanced Track B: {ORIG} -> {len(nb['cells'])} cells")
