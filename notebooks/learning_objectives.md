# Learning Objectives --- Per Notebook, Per Section

Each objective has a Bloom level and a matched assessment type.
All four plans teach the same core material; the pedagogical approach differs.

**Entry point:** Open `00_START_HERE.ipynb` to choose your plan. Every content
notebook links back to Start Here and forward to the next notebook in the plan.

**Assessment types:**
- **MCQ** (`quiz()`) --- multiple-choice with immediate feedback
- **Predict** (`predict_choice()`) --- predict an outcome before running code
- **Reflect** (`reflect()`) --- open-ended reflection graded by keywords
- **Order** (`order()`) --- rank or sequence items

All assessments are tracked by `LearningTracker` with Bloom's taxonomy levels.

---

## Plan A — Bottom-Up (3 Sequential Notebooks)

### Notebook 01: What Is an Encoded Magic State?

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. The T-state | State the T-state formula and its phase (π/4) | Remember | MCQ |
| 1. The T-state | Locate the T-state on the Bloch sphere | Understand | Predict |
| 1. The T-state | Explain why Clifford-only circuits are classically simulable | Understand | MCQ |
| 2. Seed styles | Recognise that different gate sequences produce the same state | Remember | MCQ |
| 2. Seed styles | Explain why global phase is unphysical | Understand | MCQ |
| 3. Why encode | State the no-cloning theorem and its consequence | Understand | MCQ |
| 3. Why encode | State the [[4,2,2]] code parameters (4 physical, 2 logical, distance 2) | Remember | MCQ |
| 4. Encoder circuit | Count 2-qubit gates in the cx_chain encoder | Apply | MCQ |
| 5. Full preparation | Predict how many basis states have non-zero amplitude | Understand | Predict |
| 6. Stabilisers | State the eigenvalue condition for the codespace | Remember | MCQ |
| 6. Stabilisers | Identify which stabiliser detects which error type | Apply | MCQ |
| 7. Error detection | Predict how many stabilisers a Y error triggers | Understand | Predict |
| 7. Error detection | Rank error types by number of triggered stabilisers | Analyse | Order |
| 8. Encoder comparison | Evaluate depth vs noise trade-offs between encoders | Evaluate | Reflect |
| 9. Ancilla qubits | Explain why direct measurement destroys the state | Understand | MCQ |
| 9. Ancilla qubits | Explain why three separate witness circuits are needed | Analyse | MCQ |
| 10. Ideal simulation | Predict that 100% of ideal shots pass syndrome check | Understand | MCQ |
| 11. Postselection | Identify the fundamental cost of postselection | Understand | MCQ |

### Notebook 02: How Do You Know If It Worked?

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Recap | State the stabiliser eigenvalue condition | Remember | MCQ |
| 2. Noise | Predict how noise affects the syndrome distribution | Understand | Predict |
| 3. Acceptance | Compute the shot overhead from a given acceptance rate | Apply | MCQ |
| 4. Logical operators | Explain why operators require separate circuits | Analyse | MCQ |
| 5. Magic witness | State the ideal witness value (W = 1.0) | Remember | MCQ |
| 5. Magic witness | Distinguish witness from fidelity | Understand | MCQ |
| 7. Scoring | Predict the net effect of stricter verification on score | Analyse | Predict |
| 8. Parameter sweep | Identify which parameter dominates score variation | Analyse | Reflect |
| 9. Failure modes | Rank failure modes by severity | Analyse | Order |
| 10. Factory throughput | Identify when factory scoring beats WAC | Evaluate | MCQ |

### Notebook 03: The Ratchet Learns For You

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Incumbent model | State the ratchet monotonicity guarantee | Understand | MCQ |
| 2. NeighborWalk | Describe how NeighborWalk generates challengers | Understand | MCQ |
| 3. Evaluation | Predict whether a challenger beats the incumbent | Understand | Predict |
| 4. Ratchet step | State what happens when no challenger wins | Understand | MCQ |
| 5. Lessons | Evaluate the quality of a lesson narrative | Evaluate | Reflect |
| 7. Strategies | Rank strategies from narrowest to broadest exploration | Analyse | Order |
| 8. Fix vs avoid | Distinguish 'fix' and 'avoid' search rules | Remember | MCQ |
| 9. Propagation | Explain why the winner propagates to the next rung | Understand | MCQ |
| 10. Transfer | Define what makes a transfer score 'good' | Evaluate | MCQ |

---

## Plan B — Spiral (1 Notebook, 3 Passes)

### Pass 1: The 5-Minute Demo (Remember + Understand)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1.3 Key numbers | Interpret winning margin = 0 (incumbent stays) | Remember | MCQ |
| 1.6 Score landscape | Judge whether parameter choice matters from a bar chart | Understand | Predict |

### Pass 2: Opening the Black Box (Apply + Analyse)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 2.1 T-state | State the T-state phase (π/4) | Remember | MCQ |
| 2.3 Stabiliser check | Interpret stabiliser eigenvalue +1 as codespace confirmation | Understand | MCQ |
| 2.5 Postselection | Identify the cost of postselection (lost shots) | Understand | MCQ |
| 2.9 Scoring | Explain how score balances quality and cost | Apply | Predict |
| 2.10 Challengers | State that NeighborWalk changes exactly 1 parameter | Apply | MCQ |

### Pass 3: Making It Your Own (Evaluate + Create)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 3.2 Scoring comparison | Justify when to choose factory throughput over WAC | Evaluate | Reflect |
| 3.5 Strategies | Rank strategies by ability to find multi-parameter interactions | Analyse | Order |
| 3.8 Transfer | Diagnose overfitting from a transfer score drop | Evaluate | MCQ |

---

## Plan C — Parallel Tracks (4 Notebooks)

### Dashboard (00_dashboard.ipynb)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Setup | Explain why the dashboard uses a rung-1 config as baseline | Understand | MCQ |
| 2. Exploration | Predict acceptance rate when verification = 'none' | Apply | Predict |
| 2. Exploration | Describe the quality–acceptance trade-off from exploration | Analyse | Reflect |

### Track A: Physics (track_a_physics.ipynb)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Why magic states | State the Eastin-Knill theorem | Remember | MCQ |
| 2. T-state | State the T-state phase (π/4) | Remember | MCQ |
| 3. Preparations | Explain why fidelity = 1.0 despite different amplitudes | Understand | MCQ |
| 4. [[4,2,2]] code | Derive eigenvalue constraints from S² = I | Understand | MCQ |
| 5. Logical operators | Explain why logical Y acts on 3 physical qubits | Understand | MCQ |
| 8. Error detection | Identify which stabiliser detects a Z error | Apply | Predict |
| 8. Error detection | Rank error types by stabilisers triggered | Analyse | Order |
| 9. Witness formula | State the ideal witness value (W = 1.0) | Apply | MCQ |
| 10. Witness degradation | Explain why a sharp witness peak is useful | Evaluate | Reflect |

### Track B: Engineering (track_b_engineering.ipynb)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Ideal vs noisy | Describe the visual signature of noise in a histogram | Understand | Predict |
| 2. Backend | Explain the role of the transpiler for non-native gates | Understand | MCQ |
| 3. Transpilation | Evaluate whether higher optimisation is always better | Analyse | Predict |
| 4. Cost model | Identify the dominant cost driver (2-qubit gates) | Apply | MCQ |
| 5. Acceptance | Interpret acceptance rate as fraction of passed shots | Apply | MCQ |
| 7. Failure modes | Rank failure modes by severity | Analyse | Order |
| 8. Scoring | Identify which scoring component dominates in a given regime | Evaluate | Reflect |
| 9. Factory throughput | Distinguish WAC and factory throughput by operational goal | Evaluate | MCQ |

### Track C: Search (track_c_search.ipynb)

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Parameter space | Explain why exhaustive search is impractical | Understand | MCQ |
| 2. Incumbent | Define the bootstrap incumbent | Remember | MCQ |
| 3. NeighborWalk | State that NeighborWalk changes exactly 1 parameter | Understand | MCQ |
| 4. RandomCombo | Rank strategies by interaction-finding ability | Analyse | Order |
| 6. Ratchet step | State what happens when no challenger wins | Understand | MCQ |
| 7. Patience | Explain the purpose of the patience parameter | Evaluate | MCQ |
| 8. Lessons | Evaluate the actionable insight in a lesson narrative | Evaluate | Reflect |
| 8. Rules | Distinguish 'fix' and 'avoid' search rules | Remember | MCQ |
| 10. Narrowing | Explain what search space narrowing accomplishes | Understand | MCQ |
| 12. Transfer | Diagnose overfitting from a transfer score drop | Evaluate | MCQ |

---

## Plan D — Three Claim-Driven Experiments (3 Notebooks)

### Experiment 1: Can Quantum Error Detection Protect a Magic State?

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. T-state | State the T-state phase (π/4) | Remember | MCQ |
| 2. Encoding | Predict how many basis states have non-zero amplitude | Understand | Predict |
| 3. Stabilisers | State what ⟨ZZZZ⟩ = +1 tells us (no X-type error) | Understand | MCQ |
| 4. Error detection | Identify which stabiliser detects a Z error | Apply | MCQ |
| 4. Error detection | Rank error types by stabilisers triggered | Analyse | Order |
| 5. Witness | State the ideal witness value (W = 1.0) | Apply | MCQ |
| 6. Postselection | Predict acceptance rate on ideal simulator | Understand | MCQ |

### Experiment 2: How Much Magic Survives Real-World Noise?

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Noise | Predict how noise affects the syndrome distribution | Understand | Predict |
| 2. Scoring | Explain the score tension between quality and acceptance | Analyse | MCQ |
| 3. Parameter sweep | Evaluate which optimisation level gives best score | Evaluate | Reflect |

### Experiment 3: Can a Machine Learn to Optimise?

| Section | Learning Objective | Bloom | Assessment |
|---------|-------------------|-------|------------|
| 1. Ratchet | State the ratchet monotonicity guarantee | Understand | MCQ |
| 2. Challengers | State that NeighborWalk changes exactly 1 parameter | Understand | MCQ |
| 3. Ratchet step | Predict whether a challenger beats the incumbent | Understand | Predict |
| 4. Lessons | Distinguish 'fix' and 'avoid' search rules | Remember | MCQ |
| 4. Lessons | Evaluate the actionable insight in a lesson narrative | Evaluate | Reflect |
| 5. Transfer | Diagnose overfitting from a transfer score drop | Evaluate | MCQ |
