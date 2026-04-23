# Plan C — Parallel Tracks: Choose Your Own Depth

## Overarching Theme

Plan C decomposes the [[4,2,2]] encoded magic state pipeline into three independent tracks — physics, engineering, and search — connected by a shared interactive dashboard. The learner chooses their entry point based on what they already know or what they most want to understand. Each track goes deep into one dimension of the problem; the dashboard lets them see how changes in one dimension affect the others.

This structure reflects a real truth about magic state preparation for Toffoli scalability: the physics (can the code protect the state?), the engineering (can the circuit survive hardware noise?), and the optimisation (can we find the best settings automatically?) are separable concerns that interact through a single scoring function.

## The Four Building Blocks

### Dashboard: The Control Room

An interactive widget-based interface where the learner adjusts parameters (seed style, encoder, verification, postselection, optimisation level, shots) and immediately sees the effect on four panels: circuit diagram, measurement histogram, quality metrics, and cost stats. The "Compare" button overlays multiple runs for side-by-side analysis.

**Role:** The dashboard is the empirical workbench. Each track sends the learner back here with specific "Dashboard Exercises" that make abstract concepts concrete.

### Track A: Physics — *The quantum error-detecting code*

Pure quantum mechanics, no optimisation. Covers the Eastin-Knill theorem (why you need magic states), the T-state on the Bloch sphere, three equivalent preparations, the [[4,2,2]] stabiliser code (XXXX, ZZZZ), logical operators (X_L, Y_L, Z_spectator), the encoding circuit, complete error detection (12/12 single-qubit errors), and the magic witness formula W with its sharp sensitivity peak.

**Key insight:** The witness formula's sharp peak at ⟨X_L⟩ = ⟨Y_L⟩ = 1/√2 means even moderate noise produces a noticeable drop — this sensitivity is what makes the witness a good diagnostic and what makes optimisation worthwhile.

### Track B: Engineering — *Noise, transpilation, and cost*

The bridge between ideal theory and noisy hardware. Covers noise models (IBM Brisbane's gate errors, readout errors, decoherence), transpilation at different optimisation levels (logical-to-physical gate mapping, SWAP insertion), the cost model (2Q gates dominate at 10–100× the error rate of 1Q gates), acceptance rate under noise, noisy fidelity via density matrix, failure mode classification, and the full scoring formula with its three-way tension.

Introduces factory throughput as an alternative scorer that penalises circuit cost more heavily — the right choice when you're running a magic state production pipeline rather than optimising individual states.

**Key insight:** Higher transpiler optimisation levels generally reduce gate count, but the effect is non-monotonic — aggressive routing can place operations on noisier qubit connections. The "best" level is an empirical question, not a theoretical one.

### Track C: Search — *Optimisation and the ratchet*

The automation layer. Covers the parameter space (6 dimensions, ~324 combinations), the incumbent-challenger model (monotonic guarantee), NeighborWalk (single-axis, systematic), RandomCombo (multi-axis, discovers interactions), evaluation and promotion (cheap margin threshold), full rungs with patience, lesson extraction (fix/avoid rules with confidence), LessonGuided search (rule-biased challenger generation), search space narrowing, cross-rung propagation, and transfer evaluation.

**Key insight:** The three search strategies form a progression: NeighborWalk identifies which individual parameter matters most, RandomCombo finds multi-parameter synergies, and LessonGuided focuses future search using accumulated evidence. Together they explore the space efficiently without exhaustive enumeration.

## The Arc

Plan C trusts the learner to navigate. A physicist can start at Track A and skip to the dashboard to see the numbers they just derived change under noise. An engineer can start at Track B and understand cost before caring about stabiliser algebra. A computer scientist can start at Track C and see the optimisation loop before understanding what's being optimised. The dashboard unifies all three perspectives into a single interactive view — the same view the ratchet uses internally to evaluate experiments.
