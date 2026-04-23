# Plan A — Sequential: Building the Optimiser From the Ground Up

## Overarching Theme

Plan A is the pedagogical backbone. It takes the learner from "what is a magic state?" to "a machine optimises its preparation automatically" in three sequential notebooks, each building on the last. The [[4,2,2]] code serves as a minimal but complete laboratory: small enough to understand every qubit, large enough to exhibit real error-detection and the quality-vs-cost tensions that make magic state distillation hard at scale.

## The Three Building Blocks

### Notebook 1: What Is an Encoded Magic State?

Establishes the full physical foundation. The T-state |T⟩ = (|0⟩ + e^{iπ/4}|1⟩)/√2 is the non-Clifford resource that breaks classical simulability (Gottesman-Knill theorem) and enables universal quantum computation. But a bare qubit is fragile — no cloning, no majority vote, measurement destroys.

The [[4,2,2]] code spreads the T-state across 4 physical qubits so that no single qubit carries the information alone. Stabiliser measurements (XXXX, ZZZZ) act as quantum checksums: eigenvalue +1 means "no error detected." Every single-qubit Pauli error is caught. Ancilla-based syndrome extraction reads the checksums without collapsing the encoded state, and postselection discards flagged shots.

**Key insight:** Three seed styles (h_p, ry_rz, u_magic) and two encoder styles (cx_chain, cz_compiled) all produce the same logical state. The choice is pure engineering — which transpiles to fewer noisy gates on your hardware.

### Notebook 2: How Do You Know If It Worked?

Introduces the measurement and scoring apparatus. Under IBM Brisbane noise, the ideal W=1.0 and 100% acceptance degrade. The magic witness formula W = magic_factor × spectator_factor distills three logical-operator expectations into a single quality number. But quality alone is not enough — you need to account for the shots lost to postselection and the circuit resources consumed.

The scoring formula score = quality × acceptance / cost captures this three-way tension. Different scoring functions (weighted acceptance cost vs. factory throughput) rank configurations differently depending on whether you optimise per-state quality or production-line yield. Dominant failure modes (postselection collapse, witness erosion, cost explosion) classify the biggest weakness of each configuration.

**Key insight:** The score is not a single metric but a *ratio* that forces trade-offs. Stricter verification improves quality but crashes acceptance. More complex circuits reduce noise sensitivity but inflate cost. The scoring formula surfaces whichever factor is the current bottleneck.

### Notebook 3: The Ratchet Learns For You

Closes the loop with automated search. The incumbent-challenger model is monotonic: the best-so-far configuration never gets worse. NeighborWalk changes one parameter at a time (systematic, blind to interactions). RandomCombo mutates multiple parameters (discovers synergies). LessonGuided uses fix/avoid rules from previous rungs to bias search toward promising regions.

Cross-rung propagation transfers the winner and accumulated lessons forward, and search space narrowing prunes values that consistently hurt. Transfer evaluation across different backend noise profiles ensures the ratchet learned general principles, not hardware-specific quirks.

**Key insight:** The ratchet compresses hours of manual parameter exploration into minutes of automated search. Each rung produces human-readable lessons and machine-readable rules that make future exploration more efficient — a self-improving loop.

## The Arc

Plan A's progression mirrors the research pipeline itself: understand the physics (what are we building?), build the instrumentation (how do we measure success?), then automate the search (let the machine find the best settings). By the end, the learner has seen every number the harness produces and knows exactly what it means.
