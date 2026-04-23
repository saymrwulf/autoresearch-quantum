# Plan B — Spiral: Three Passes Through the Same Machine

## Overarching Theme

Plan B is built on a single pedagogical bet: you learn a complex system best by seeing it three times at increasing depth. The [[4,2,2]] encoded magic state pipeline — from T-state preparation through error detection to automated ratchet optimisation — is presented as a single notebook with three concentric passes. Each pass covers the *entire* system, but what was a black box in Pass 1 becomes transparent machinery in Pass 2 and a tool you drive in Pass 3.

## The Three Building Blocks

### Pass 1: The 5-Minute Demo — *Run the machine, see it work, get curious.*

The learner loads a config, runs a ratchet step, and sees a winner emerge with a score and a lesson narrative. No explanation — just output. A bar chart shows score variation across experiments. The point: something interesting is happening, and every number on screen is a question waiting to be asked.

**What you see:** A JSON step result, a winning margin, a lesson string, a score landscape bar chart. None of it makes sense yet — and that's the design.

### Pass 2: Opening the Black Box — *Build understanding from the ground up, but always connecting back.*

Now we rewind. The T-state is built from scratch on the Bloch sphere. The [[4,2,2]] encoding spreads it across 4 qubits. Stabilisers act as checksums. Syndrome extraction via ancillas enables postselection without destroying the state. Noise from IBM Brisbane degrades acceptance and witness. The magic witness formula and scoring function are computed by hand.

Every number from Pass 1 is re-encountered with full physical meaning: "that bar chart score of 0.058 came from quality 0.73 × acceptance 0.77 / cost 9.54." The challengers from the ratchet step are shown as single-parameter mutations of the incumbent. Promotion requires beating the incumbent by a margin.

**Key insight:** Pass 2 doesn't introduce new material — it reveals the structure that was always there in the Pass 1 output. The learner's own curiosity from Pass 1 drives engagement.

### Pass 3: Making It Your Own — *Modify parameters, compare scoring functions, design experiments.*

The learner now drives: narrowing the search space, comparing WAC vs factory throughput scoring, running multi-step rungs with patience, visualising exploration trajectories, and testing transfer across backends. Code challenges ask the learner to compute cumulative best scores, create search rules, and design custom experiments that compete against the ratchet's winner.

**Key insight:** The same system that was opaque in Pass 1 and explained in Pass 2 is now a tool the learner can bend to their own questions. The spiral completes: each pass through the same material reveals structure that was invisible before.

## The Arc

The spiral structure mirrors how the ratchet itself works — each step builds on what came before, ratcheting toward deeper understanding. Pass 1 creates questions. Pass 2 answers them. Pass 3 shows that the answers are levers you can pull. The magic state preparation pipeline is both the subject and the metaphor.
