# Plan D — Hypothesis-Driven: Precision-Engineering the Magic State Factory

## Overarching Theme

The Toffoli gate — the workhorse of fault-tolerant quantum arithmetic — consumes magic states. Every Toffoli decomposition burns multiple |T⟩ states via gate teleportation. At scale, this creates a **supply-chain bottleneck**: a useful quantum algorithm may need millions of high-fidelity magic states, each of which must be prepared, encoded, verified, and distilled before consumption.

Plan D puts the **preparation stage** of that pipeline under a microscope using the experimental method: hypothesis → claims → proof.

## The Three Building Blocks

### Experiment 1: Protection — *Can we even build the product?*

Proves the [[4,2,2]] code can encode |T⟩ with W=1.0, detect all 12 single-qubit errors, and postselect cleanly. This is the **existence proof**: the factory blueprint works in principle.

- Magic witness W = 1.0 (perfect preservation)
- Both stabilisers (XXXX, ZZZZ) at +1
- 12/12 single-qubit Pauli errors detected
- 100% acceptance on ideal simulator

### Experiment 2: Noise — *How does the factory perform under real conditions?*

Under IBM Brisbane noise, quality and yield both drop. But critically, the score varies 2–5× across parameter choices (transpiler level alone). This proves that **minor knob-turns in the preparation circuit have outsized effects on output quality** — the creation process is sensitive enough that optimisation is both necessary and worthwhile.

- Noise reduces W below 1.0 and acceptance below 100%
- The scoring formula score = quality × acceptance / cost captures the three-way trade-off
- Parameter sweep reveals significant score variation across optimisation levels

### Experiment 3: Optimisation — *Can we automate the tuning?*

A ratchet optimizer searches the 6+ dimensional parameter space (seed style, encoder, verification, postselection, transpiler settings), monotonically improving and extracting fix/avoid rules. The winning configuration transfers to unseen backends — meaning it learned **general principles of magic state preparation**, not noise-specific hacks.

- Ratchet improves monotonically (incumbent never gets worse)
- Actionable lessons extracted (fix/avoid rules with confidence scores)
- Winning configuration beats the manual default
- Configuration transfers to different noise contexts

## Why This Matters for Toffoli Scalability

The Toffoli consumption problem is ultimately a **throughput × fidelity** problem. If each magic state arriving at the Toffoli teleportation step is slightly noisier than needed, you either:

- Need more rounds of distillation (exponential overhead), or
- Accept lower gate fidelity (computation fails)

By showing that small adjustments to the preparation circuit — encoder style, verification strategy, transpiler level — produce 2–5× score differences, Plan D demonstrates that **the bottleneck is addressable at the source**. You don't just distill harder; you prepare smarter. The ratchet automates finding those smarter settings, and the fact that its lessons transfer means you can pre-optimize before ever touching real hardware.

**In short:** Plan D proves that magic state creation is a tunable, optimizable process — not a fixed-cost overhead — and that's the lever for making Toffoli-heavy computation scale.
