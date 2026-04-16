# The Story of autoresearch-quantum

## What this system does, in one paragraph

This is a machine that discovers, by itself, the best way to prepare an
encoded magic state on the [[4,2,2]] quantum error-detecting code. You give
it a starting recipe and a search space of alternatives. It runs hundreds of
simulated quantum experiments, scores them, learns which choices help and
which choices hurt, narrows the search, and climbs to the best recipe it can
find -- then hands you a written lesson explaining what it learned and why.
The entire loop -- propose, evaluate, compare, learn, repeat -- runs without
human intervention. That is the "auto" in autoresearch.


---


## Part 1: The quantum computing problem

### 1.1 What is a magic state?

Fault-tolerant quantum computers need a special ingredient called a **magic
state** to perform the T gate -- the non-Clifford gate that makes quantum
computation universal. You cannot create this state using Clifford operations
alone, so you prepare a noisy approximation and then **distill** it into a
high-fidelity copy. The preparation step is the bottleneck: if your raw magic
states are junk, distillation is expensive or impossible.

### 1.2 What is the [[4,2,2]] code?

The [[4,2,2]] code is the smallest quantum error-detecting code. It uses 4
physical qubits to encode 2 logical qubits. It cannot correct errors, but it
can *detect* them: if an error flips one qubit, the code's stabilizers
(XXXX and ZZZZ) flag it, and you can throw the shot away. This
**postselection** raises quality at the cost of throughput.

The code has two logical qubits. We use one to carry the magic state and the
other as a **spectator** -- an untouched qubit whose Z-measurement tells us
whether the encoding process corrupted the logical subspace.

### 1.3 What knobs does this system turn?

An experiment recipe (called an `ExperimentSpec`) has ~15 tuneable dimensions:

| Dimension | What it controls | Example values |
|---|---|---|
| `seed_style` | How the raw T-state is prepared on qubit 0 | `h_p`, `ry_rz`, `u_magic` |
| `encoder_style` | How the 4-qubit encoding circuit is built | `cx_chain`, `cz_compiled` |
| `verification` | Which stabilizers are measured before readout | `both`, `z_only`, `x_only`, `none` |
| `postselection` | Which syndrome outcomes cause a shot to be discarded | `all_measured`, `z_only`, `none` |
| `ancilla_strategy` | Whether verification uses 1 reused or 2 dedicated ancillas | `dedicated_pair`, `reused_single` |
| `optimization_level` | Qiskit transpiler aggressiveness | 1, 2, 3 |
| `layout_method` | Physical qubit placement algorithm | `sabre`, `dense` |
| `routing_method` | SWAP insertion algorithm | `sabre`, `basic` |
| `target_backend` | Which IBM device topology to compile for | `fake_brisbane`, `fake_kyoto`, ... |
| `shots` | Samples per circuit | 256 -- 4096 |

The question the system answers: **Which combination of these choices gives
the highest-quality encoded magic states at the lowest cost?**

### 1.4 How is each experiment evaluated?

For each `ExperimentSpec`, the executor:

1. **Builds four circuits** (`encoded_magic_state.py`):
   - `acceptance` -- measures all data qubits in the Z basis after
     verification, to compute the postselection acceptance rate.
   - `logical_x` -- rotates into the X basis before measurement, to get
     `<X_L>` on the magic-carrying logical qubit.
   - `logical_y` -- rotates into the Y basis, to get `<Y_L>`.
   - `spectator_z` -- measures the spectator logical qubit in Z, to get
     `<Z_spectator>`.

2. **Transpiles** them for the target backend's coupling map and basis gates.

3. **Simulates** them on Qiskit Aer with the backend's calibrated noise model,
   repeating the configured number of times with independent random seeds.

4. **Postselects**: for each shot, checks the syndrome register. Shots where
   the stabiliser flagged an error are discarded. What remains is the
   postselected ensemble.

5. **Computes metrics** from the postselected data:

   | Metric | Formula | What it measures |
   |---|---|---|
   | `logical_magic_witness` | `((1 + (X_L + Y_L)/sqrt(2)) / 2) * ((1 + Z_spectator) / 2)` | Magic-state quality, penalised if spectator is disturbed |
   | `acceptance_rate` | `accepted_shots / total_shots` | Throughput (what fraction survives postselection) |
   | `stability_score` | `1 - pstdev(repeat_scores) / mean(repeat_scores)` | Consistency across independent repeat runs |
   | `noisy_encoded_fidelity` | `Tr(rho_noisy \| target><target \|)` via density matrix simulation | How close the noisy state is to the ideal encoded T-state |
   | `codespace_rate` | Mean acceptance across all four circuit types | Overall codespace survival |
   | `two_qubit_count`, `depth` | From the transpiled circuits | Cost proxies |

6. **Scores** the experiment by combining these metrics into a single scalar:

   ```
   score = (quality * acceptance_rate) / cost
   ```

   where `quality` is a weighted sum of the metrics above (weights are
   per-rung, configured in YAML) and `cost` accounts for gate count, depth,
   shots, and estimated runtime.


---


## Part 2: The autoresearch engine (the meta layer)

This is a direct implementation of the **Karpathy autoresearch pattern**: an
automated loop that does what a diligent PhD student would do -- try things,
keep what works, learn why, zoom in, try harder things.

### 2.1 The ratchet metaphor

A ratchet is a mechanism that only moves forward. In this system:

- The **incumbent** is the best experiment found so far.
- Each **step**, the system generates **challengers** -- modified versions of
  the incumbent -- evaluates them, and replaces the incumbent only if a
  challenger beats it by a configured margin.
- The incumbent can only improve. It never regresses.

A **rung** is a complete search campaign: multiple ratchet steps, with a
patience counter that stops the rung early if the incumbent stops improving.

A **full ratchet** runs multiple rungs in sequence, each one asking a
progressively harder question.

### 2.2 The five rungs

```
Rung 1: "What preparation recipe works at all?"
  |
  | winner propagates down
  v
Rung 2: "Is it stable across noisy backends?"
  |
  | winner propagates down, search space narrows
  v
Rung 3: "Does it transfer to other devices?"
  |
  | winner propagates down, search space narrows further
  v
Rung 4: "What maximises throughput per cost?"
  |
  | winner propagates down, only proven dimensions survive
  v
Rung 5: "Which heuristics are load-bearing for distillation?"
```

Each rung is a YAML file (`configs/rungs/rung1.yaml` through `rung5.yaml`)
that configures:
- What to search over (the dimension grid)
- How to score (which quality metrics matter most)
- How hard to search (step budget, patience, promotion rules)
- Where to start (bootstrap incumbent)

The key insight: **the output of the system is not just the best circuit**.
It is the best circuit *plus a machine-readable set of rules* about what
worked and why, formatted so the next rung (or the next human) can pick up
where the machine left off.

### 2.3 The search strategies

The original Codex implementation had a single strategy: change one knob at
a time and see if the score improves. This is local hill-climbing. It
plateaus after one pass through the neighbours.

The new system uses a **composite generator** that allocates its budget
across three strategies:

| Strategy | Weight | What it does |
|---|---|---|
| `NeighborWalk` | 40% | Classic single-axis perturbation. Reliable, no surprises. |
| `RandomCombo` | 30% | Picks 1--3 dimensions at random and mutates them simultaneously. Escapes local optima by making multi-axis jumps. |
| `LessonGuided` | 30% | Reads the `SearchRule` directives from previous rungs. Fixes dimensions that are proven. Avoids values that are proven bad. Samples preferred values with probability proportional to confidence. |

When no lessons exist yet (rung 1), `RandomCombo` gets 60% of the budget
to maximise early exploration.

Every generated candidate is checked against a **history set** of all
previously evaluated fingerprints. The system never wastes a slot evaluating
a spec it has already seen.

### 2.4 The lesson feedback loop

After each rung completes, two artefacts are produced:

1. **RungLesson** (human-readable): a Markdown narrative that says things like
   *"verification=z_only improved mean score by +0.0312 over 8 runs"* and
   *"Consider probing remaining ancilla_strategy values."*

2. **LessonFeedback** (machine-readable): a list of `SearchRule` objects:

   ```
   SearchRule(dimension="verification", action="prefer", value="z_only",
              confidence=0.67, reason="mean score 0.1823 is +0.0312 above overall mean")

   SearchRule(dimension="seed_style", action="fix", value="ry_rz",
              confidence=0.60, reason="all top-3 experiments use seed_style=ry_rz")

   SearchRule(dimension="verification+postselection", action="prefer",
              value=("z_only", "z_only"), confidence=0.33,
              reason="interaction effect +0.0089 (joint=+0.0401, expected_additive=+0.0312)")
   ```

   The rules come from three analyses:
   - **Per-dimension mean effects**: for each value of each dimension, compute
     the mean score minus the overall mean. Positive = prefer, negative = avoid.
   - **Fix detection**: if the top-K experiments all share a value, and that
     value outperforms alternatives, emit a "fix" rule.
   - **Interaction detection**: for each pair of dimensions, check whether the
     joint effect exceeds the sum of the two marginal effects. If so, there is
     a synergy (or conflict) between those two choices.

These rules feed directly into the `LessonGuided` strategy in the next rung.
They also feed into `narrow_search_space()`, which prunes "avoid" values and
constrains "fix" dimensions, physically shrinking the grid the next rung
searches over.

### 2.5 Cross-rung propagation

When `run_ratchet()` finishes rung N and begins rung N+1:

1. The **winner spec** from rung N becomes the bootstrap incumbent for rung N+1.
   The human-written YAML bootstrap is overridden. (A `propagated_spec.json` is
   saved for traceability.)

2. The **accumulated SearchRules** from all completed rungs are combined and
   used to narrow the search space of rung N+1.

3. The `LessonGuided` strategy in rung N+1 has access to rules from *all*
   previous rungs, not just the most recent one.

This is the "ratchet" in action across rungs: the system starts broad, learns
what matters, and zooms in.

### 2.6 The two scoring functions

| Score function | Used by | Formula | Optimises for |
|---|---|---|---|
| `weighted_acceptance_cost` | Rungs 1--3 | `(quality * acceptance) / cost` | Best magic-state quality at reasonable cost |
| `factory_throughput` | Rungs 4--5 | `(acceptance * witness) / cost` (heavier cost penalty) | Accepted states per unit cost, as a proxy for distillation factory yield |

The factory score also computes `FactoryMetrics` (accepted per shot, logical
error per accepted, cost per accepted, throughput proxy) and attaches them to
the experiment record for downstream analysis.

### 2.7 Transfer evaluation

Rung 3 can optionally run in **transfer mode**: instead of searching over
backends as a dimension (which just finds the easiest backend), it evaluates
the *same spec* across multiple backends and scores it by the **minimum**
(pessimistic) score. A spec that scores 0.18 on Brisbane and 0.02 on Kyoto
gets a transfer score of 0.02, not 0.10. This prevents backend overfitting.

```
python -m autoresearch_quantum run-transfer \
  --config configs/rungs/rung3.yaml \
  --backends fake_brisbane fake_kyoto fake_sherbrooke
```

### 2.8 Resumability

Every ratchet step saves a `progress.json` checkpoint:

```json
{
  "rung": 2,
  "steps_completed": 2,
  "patience_remaining": 1,
  "current_incumbent_id": "r2-incumbent-a1b2c3d4e5",
  "completed": false
}
```

If the process crashes or you Ctrl-C, re-running the same rung picks up from
the last completed step with the correct patience counter. No work is lost.


---


## Part 3: Claims and how the tests prove them

### Claim 1: The encoded state is a valid magic state in the [[4,2,2]] code.

**Test**: `test_encoded_target_state_satisfies_stabilizers`

Constructs the ideal encoded magic statevector and checks that both
stabilizers (XXXX and ZZZZ) have expectation value exactly 1.0. If the
encoding circuit were wrong, at least one stabilizer would not be +1.

### Claim 2: The circuit bundle measures the right observables.

**Test**: `test_circuit_bundle_contains_expected_contexts`

Verifies that `build_circuit_bundle()` produces exactly the four expected
circuits (logical_x, logical_y, spectator_z, acceptance), each with correct
metadata. If a measurement basis rotation were missing or a circuit were
mislabelled, this catches it.

### Claim 3: Noisy simulation produces meaningful scores.

**Test**: `test_local_executor_produces_score`

Runs a full evaluation (build circuits, transpile, simulate with noise,
postselect, compute witness, score) and checks that the score is positive and
the acceptance rate and witness are in [0, 1]. This is an integration test of
the entire evaluation pipeline -- if any piece is broken, the score collapses.

### Claim 4: The challenger generator explores the search space correctly.

**Tests**: `test_neighbor_challengers_mutate_single_dimension`,
`test_neighbor_walk_respects_history`,
`test_random_combo_generates_multi_axis_mutations`,
`test_lesson_guided_uses_rules`,
`test_composite_generator_combines_strategies`

These verify:
- NeighborWalk changes exactly one field per challenger.
- Passing a history set of already-seen fingerprints produces zero
  duplicates.
- RandomCombo produces at least one challenger with >1 changed field (the
  defining property of multi-axis mutation).
- LessonGuided respects "fix" rules: when told to fix `seed_style=ry_rz`,
  every generated challenger has that value.
- The composite generator stays within the budget cap.

### Claim 5: The lesson system extracts correct prefer/avoid/fix rules.

**Tests**: `test_extract_search_rules_prefer_and_avoid`,
`test_narrow_search_space_removes_avoided`,
`test_build_lesson_feedback_end_to_end`

Given synthetic experiment records where `z_only` scores 0.80--0.85 and
`both` scores 0.50--0.55, the extractor must emit a "prefer z_only" and
"avoid both" rule. `narrow_search_space` must actually remove avoided values
and constrain fixed dimensions.

### Claim 6: The factory score function computes throughput metrics.

**Tests**: `test_factory_throughput_score_produces_metrics`,
`test_score_registry_has_factory`

Given known input metrics (acceptance 0.70, witness 0.80), verifies that
`factory_throughput_score` produces a positive score, attaches
`factory_metrics` to the `extra` dict, and that `accepted_states_per_shot`
equals the input acceptance rate.

### Claim 7: Transfer evaluation runs the same spec across backends.

**Test**: `test_transfer_evaluator_runs_across_backends`

Runs a transfer evaluation on a single backend (for speed) and checks that a
`TransferReport` is returned with a positive transfer score and the correct
backend key in `per_backend_scores`.

### Claim 8: Progress and feedback survive serialisation round-trips.

**Tests**: `test_save_and_load_progress`,
`test_save_and_load_lesson_feedback`

Writes a `RungProgress` / `LessonFeedback` to disk via the store, reads it
back, and verifies all fields match. If the JSON schema or the
deserialisation logic drifts, this catches it.

### Claim 9: A full rung saves progress and produces both lesson types.

**Tests**: `test_run_rung_saves_progress`,
`test_run_rung_returns_lesson_and_feedback`

Runs a complete rung (bootstrap + steps + lesson extraction) and checks that
`progress.json` exists and is marked `completed`, and that the return value
includes both a human-readable `RungLesson` and a machine-readable
`LessonFeedback`.

### Claim 10: Multi-rung ratchet propagates winners and accumulates lessons.

**Test**: `test_run_ratchet_propagates_winner`

Runs a two-rung ratchet and checks that:
- Both rungs produce (lesson, feedback) tuples.
- `harness._accumulated_lessons` contains entries from both rungs, proving
  that rung 2 had access to rung 1's rules when generating challengers.

### Claim 11: Different specs get different simulator seeds.

**Test**: `test_different_specs_get_different_seeds`

The old code used `seed_simulator = 11_000 + repeat_index`, meaning every
spec got the same random stream. The new code hashes the spec's fingerprint
into the seed. This test creates two specs that differ only in `verification`
and checks that their computed seeds are different.


---


## Part 4: The teaching layer

The system is not only a research engine. It is also a course. Twelve Jupyter
notebooks, organised into four independent learning plans, teach the same
material through different pedagogical lenses. The teaching layer sits on top
of the research engine and uses its real components (circuits, simulators,
scorers, ratchet) as the substrate for interactive learning.

### 4.1 Entry point: 00_START_HERE.ipynb

Every learner begins at `notebooks/00_START_HERE.ipynb`. This notebook
contains no code --- it is a plan selector. It describes the four plans, their
target audiences, and links directly to each plan's first notebook. All
content notebooks link back to Start Here.

### 4.2 The four plans

| Plan | Style | Notebooks | Target learner |
|------|-------|-----------|----------------|
| **A** | Bottom-up, sequential | 3 | Methodical learners who want foundations first |
| **B** | Spiral, three passes | 1 (78 cells) | Time-pressed learners who want a demo first, theory later |
| **C** | Parallel tracks + dashboard | 4 | Learners who want to choose their own path |
| **D** | Hypothesis-driven experiments | 3 | Research-oriented learners who want to test claims |

All four plans cover the same core concepts: T-state preparation, [[4,2,2]]
encoding, stabiliser verification, postselection, scoring, the ratchet
optimiser, lesson extraction, and cross-rung transfer.

### 4.3 Interactive assessments (teaching/assess.py)

Every content notebook includes interactive assessments built with ipywidgets:

- **quiz()** --- multiple-choice questions with immediate feedback
- **predict_choice()** --- "What do you think will happen?" before running code
- **reflect()** --- open-ended reflections graded by keyword matching
- **order()** --- drag-and-drop ordering exercises (e.g., rank error types)

Each assessment is tagged with a Bloom's taxonomy level (remember, understand,
apply, analyse, evaluate) and a topic. The full mapping of learning objectives
to assessments is documented in `notebooks/learning_objectives.md`.

### 4.4 Progress tracking (teaching/tracker.py)

Each notebook creates a `LearningTracker` instance that records:

- scores per assessment (correct/incorrect, attempt count)
- Bloom's level distribution (how many of each level attempted/passed)
- time spent per assessment
- checkpoint summaries at natural breakpoints

At the end of each notebook, `tracker.dashboard()` displays a visual summary,
and `tracker.save()` persists progress to a JSON file. Progress files can be
reset with `bash scripts/app.sh reset`.

### 4.5 Navigation

Every content notebook has a navigation footer with:

- **Forward link** to the next notebook in the plan
- **Back-link** to 00_START_HERE.ipynb
- **Cross-plan suggestions** at terminal notebooks (e.g., "Finished Plan A?
  Try Plan D for a different perspective.")

### 4.6 Pedagogical quality enforcement

The test suite includes `tests/test_pedagogy.py`, which enforces educational
quality invariants across all content notebooks:

- Minimum 200 words of prose per notebook
- At least 25% of cells are markdown (not code-only)
- Every notebook has a title header and multiple sections
- At least 2 interactive assessments per notebook
- At least 2 different assessment types per notebook (variety)
- Bloom's taxonomy coverage: at least 2 levels per notebook
- Checkpoint summaries present when a notebook has 4+ assessments
- LearningTracker initialisation, dashboard(), and save() in every notebook
- Key Insight callouts in longer notebooks (5+ sections)
- All four plans collectively cover core concepts (stabiliser, magic, witness, ratchet)

These tests catch pedagogical regressions the same way unit tests catch code
regressions. Adding a new notebook or modifying an existing one will fail CI
if it violates these invariants.


---


## Part 5: The consumer experience (app.sh)

The project includes a lifecycle manager (`scripts/app.sh`) that handles the
entire consumer experience from first clone to running notebooks:

```bash
bash scripts/app.sh bootstrap           # venv, pip install, kernel registration, import check
bash scripts/app.sh start               # launch JupyterLab in background, open browser
bash scripts/app.sh start --foreground  # run in foreground (Ctrl-C to stop)
bash scripts/app.sh start --no-open     # launch without opening browser
bash scripts/app.sh start --port 9999   # use a specific port
bash scripts/app.sh stop                # graceful shutdown (SIGTERM, wait, SIGKILL fallback)
bash scripts/app.sh restart             # stop + start
bash scripts/app.sh status              # venv, server, ports, orphan detection
bash scripts/app.sh validate            # ruff + mypy + full test suite
bash scripts/app.sh validate --quick    # lint + type check + unit tests only
bash scripts/app.sh logs [-f]           # show or follow JupyterLab output
bash scripts/app.sh reset               # delete learner progress files
bash scripts/app.sh reset-state         # reset Jupyter runtime + UI state
```

Bootstrap checks Python >= 3.11, creates the venv, installs the package with
dev and notebook dependencies, registers a Jupyter kernel with `--sys-prefix`
(venv-local, not user-global), and verifies that core imports succeed.

**Start runs Jupyter in the background by default.** The process survives
terminal close. The terminal prints the URL and returns immediately --- you are
free to close the tab or use it for other work. Jupyter keeps running until you
explicitly stop it with `app.sh stop`. The `--foreground` flag is the
alternative: it occupies the terminal, and Ctrl-C or closing the tab stops
Jupyter cleanly with no orphan process left behind.

Start finds a free port by scanning 8888-8899 via `lsof`, writes a PID file
at `.logs/jupyter.pid`, and opens the browser directly to
`00_START_HERE.ipynb`. All Jupyter state (config, data, runtime, IPython,
matplotlib cache) is isolated into project-local directories, preventing
cross-project interference.

This project follows the [JupyterManager](https://github.com/saymrwulf/JupyterManager)
lifecycle specification. The cross-project `jupyter-hub` CLI can discover and
manage this project alongside other Jupyter-enabled projects:

```bash
jupyter-hub status        # show all projects (running/stopped)
jupyter-hub ports         # port allocation map (8888-8899)
jupyter-hub stop-all      # stop all Jupyter instances
jupyter-hub orphans       # find untracked processes
jupyter-hub kill-orphans  # kill them
```

Validation runs the full quality pipeline: ruff linting, mypy strict type
checking, and the pytest suite (335 tests, excluding browser UX by default).
The `--quick` flag runs only lint, type check, and unit tests.


---


## Part 6: The file map

```
autoresearch-quantum/
  configs/rungs/
    rung1.yaml             Baseline: what recipe works at all?
    rung2.yaml             Stability: does it hold under noise variation?
    rung3.yaml             Transfer: does it work on other devices?
    rung4.yaml             Factory: what maximises throughput per cost?
    rung5.yaml             Rosenfeld: which heuristics are load-bearing?

  src/autoresearch_quantum/
    models.py              Every data structure in one file
    config.py              YAML -> RungConfig parser
    cli.py                 Entry point: run-experiment, run-step, run-rung,
                           run-ratchet, run-transfer

    codes/
      four_two_two.py      The [[4,2,2]] code: stabilizers, logical ops,
                           encoder circuits, magic seed gates

    experiments/
      encoded_magic_state.py   Builds the four-circuit measurement bundle

    execution/
      local.py             LocalCheapExecutor: Aer noise simulation
      hardware.py          IBMHardwareExecutor: real-device SamplerV2
      transfer.py          TransferEvaluator: same spec across N backends
      analysis.py          Postselection, eigenvalues, witness formula
      backends.py          Backend resolution (fake_* or IBM runtime)
      transpile.py         Transpilation, gate counting, runtime estimates

    scoring/
      score.py             weighted_acceptance_cost + factory_throughput

    search/
      challengers.py       GeneratedChallenger, neighbor generation, dedup
      strategies.py        NeighborWalk, RandomCombo, LessonGuided,
                           CompositeGenerator

    lessons/
      extractor.py         Human-readable RungLesson + machine LessonFeedback
      feedback.py          SearchRule extraction, interaction detection,
                           search space narrowing

    ratchet/
      runner.py            AutoresearchHarness: the orchestrator

    persistence/
      store.py             JSON file store: experiments, steps, progress,
                           lessons, feedback, propagated specs

    teaching/
      assess.py            Widget-based quizzes, predictions, reflections
      tracker.py           LearningTracker: per-student progress tracking

  notebooks/
    00_START_HERE.ipynb    Central entry point: plan selector
    learning_objectives.md Per-notebook, per-section learning objectives
    plan_a/                Bottom-up: 3 sequential notebooks
    plan_b/                Spiral: 1 notebook, 3 passes
    plan_c/                Parallel tracks + dashboard: 4 notebooks
    plan_d/                Hypothesis-driven: 3 experiments

  paper/
    autoresearch_quantum.tex   Technical paper (LaTeX, 19 pages)
    compendium.tex             Companion textbook (LaTeX, 36 pages)

  scripts/
    app.sh                 Consumer lifecycle manager (bootstrap/start/stop/validate)

  tests/                   335 tests across 13 files
    test_analysis.py       Postselection & witness
    test_browser_ux.py     Playwright end-to-end UX
    test_cli.py            CLI subcommands
    test_codes.py          [[4,2,2]] code correctness
    test_config.py         YAML config loading
    test_experiments.py    Circuit bundle construction
    test_feedback.py       Lesson extraction & search rules
    test_harness.py        Full ratchet integration
    test_notebooks.py      Notebook execution & structure
    test_pedagogy.py       Pedagogical quality invariants (130 tests)
    test_persistence.py    JSON store round-trips
    test_scoring.py        Score functions
    test_teaching.py       Assessment widgets & tracker

  .github/workflows/ci.yml  CI: lint, type check, test matrix, notebook execution
  .pre-commit-config.yaml   Ruff, mypy, nbstripout, hygiene hooks

  data/                    Output directory (created at runtime)
    default/
      rung_1/
        experiments/       One JSON per evaluated spec
        ratchet_steps/     One JSON per step
        incumbent.json     Current best
        progress.json      Resumability checkpoint
        lesson.json        Machine-readable lesson
        lesson.md          Human-readable narrative
        lesson_feedback.json   SearchRules for the next rung
      rung_2/
        propagated_spec.json   Winner carried from rung 1
        ...
```


---


## Part 7: How to use it without Claude

You do not need an AI to run this system or to make progress with its
output. Everything below runs in your terminal.

### 7.1 Setup

```bash
cd autoresearch-quantum
bash scripts/app.sh bootstrap
```

This creates the venv, installs all dependencies, registers the Jupyter kernel,
and verifies imports. If you prefer manual setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebooks]"
```

### 7.2 Run a single experiment

```bash
python -m autoresearch_quantum run-experiment \
  --config configs/rungs/rung1.yaml \
  --set verification=z_only \
  --set seed_style=ry_rz
```

This prints a JSON result with the score, failure mode, and experiment ID.
The full record is saved to `data/default/rung_1/experiments/`.

### 7.3 Run one ratchet step

```bash
python -m autoresearch_quantum run-step \
  --config configs/rungs/rung1.yaml
```

This bootstraps an incumbent (if none exists), generates challengers, evaluates
them, promotes the best, and saves the step record. Run it again and it
generates *new* challengers (never repeating), with a new incumbent if one was
found.

### 7.4 Run a full rung

```bash
python -m autoresearch_quantum run-rung \
  --config configs/rungs/rung1.yaml
```

Runs up to `step_budget` steps (default 3), stopping early if patience runs
out. Produces `data/default/rung_1/lesson.md` -- read this file. It tells you
what helped, what hurt, what seems invariant, and what to test next.

### 7.5 Run the full five-rung ratchet

```bash
python -m autoresearch_quantum run-ratchet \
  --config configs/rungs/rung1.yaml \
  --config configs/rungs/rung2.yaml \
  --config configs/rungs/rung3.yaml \
  --config configs/rungs/rung4.yaml \
  --config configs/rungs/rung5.yaml
```

This is the full pipeline. Each rung's winner is automatically propagated to
the next rung. Each rung's lessons narrow the search space for the next.
When it finishes, you have five lesson files and a final optimised recipe.

### 7.6 Run a transfer evaluation

```bash
python -m autoresearch_quantum run-transfer \
  --config configs/rungs/rung3.yaml \
  --backends fake_brisbane fake_kyoto fake_sherbrooke
```

Tests a single spec across multiple backend noise models. The output tells you
the per-backend scores and the pessimistic transfer score.

### 7.7 Reading the output

After a ratchet run, the most valuable artefacts are:

| File | What to do with it |
|---|---|
| `rung_N/lesson.md` | Read it. It is a structured report. The "What Helped" section tells you which settings to keep. The "What Hurt" section tells you what to stop trying. |
| `rung_N/lesson_feedback.json` | This is the machine-readable version. Open it and look at the `rules` array. Each rule has an `action` (prefer/avoid/fix), a `dimension`, a `value`, a `confidence` (0--1), and a `reason`. |
| `rung_N/incumbent.json` | Contains the `experiment_id` of the current best spec. Load the corresponding file from `experiments/` to see its full spec and scores. |
| `rung_N/propagated_spec.json` | The spec that was carried forward from the previous rung. Compare it with the YAML bootstrap to see what the system changed. |
| `rung_N/progress.json` | If the run was interrupted, this tells you where it left off. Just re-run the same command to resume. |

### 7.8 Making manual progress with the artefacts

The system is designed so that you can interleave human intuition with
automated search:

1. **Read the lesson.** If rung 1 says `verification=z_only` consistently
   helps, you now know something about the physics: X-stabiliser checking
   adds gate cost without enough quality payoff at this noise level.

2. **Edit the YAML.** Remove values that the lesson says to avoid. Add new
   values you want to explore. Change the weights if you care more about
   throughput than fidelity. Save the file and re-run.

3. **Run single experiments.** If you have a specific hypothesis
   ("What if `approximation_degree=0.95` helps?"), test it directly with
   `run-experiment --set approximation_degree=0.95`. The result is saved to
   the store and will be included in the next lesson extraction.

4. **Resume interrupted runs.** If your laptop dies mid-rung, just re-run the
   same command. Progress is checkpointed after every step.

5. **Compare across rungs.** Open `rung_1/lesson_feedback.json` and
   `rung_3/lesson_feedback.json` side by side. Rules that appear in both with
   high confidence are load-bearing. Rules that appear in rung 1 but vanish by
   rung 3 were artefacts of the initial noise model.

6. **Feed results to a new search.** Copy the `best_spec_fields` from
   `lesson_feedback.json` into a new YAML config as the bootstrap incumbent.
   Define a tighter search space around the winning region. Run another rung.
   You are now doing what the system does in `run_ratchet` -- but with human
   judgement about what to explore next.

### 7.9 Running the tests

```bash
# Full validation (recommended)
bash scripts/app.sh validate

# Or directly with pytest
python -m pytest tests/ -v
```

All 335 tests should pass (browser UX tests excluded by default). If a test
fails after you edit a YAML config, the most likely cause is that you
introduced a dimension value that does not correspond to an implemented code
path (e.g., `encoder_style: "rzz_lattice"` does not exist in
`four_two_two.py`).


---


## Part 8: What this system does NOT do (yet)

- **It does not run on real quantum hardware by default.** The
  `IBMHardwareExecutor` exists and is wired up, but `enable_hardware: false`
  in every config. Set it to `true` and provide credentials via the
  `QISKIT_IBM_TOKEN` environment variable to use real devices.

- **It does not do distillation.** Rung 5 (Rosenfeld Direction) identifies
  which heuristics matter for factory-style workflows, but it does not
  actually build a distillation circuit. That is the next project.

- **It does not use LLMs in the loop.** The "auto" is algorithmic
  (statistical rule extraction + guided search), not generative. There is no
  GPT/Claude call inside the ratchet loop. The intelligence is in the
  `SearchRule` extraction, the `CompositeGenerator` budget allocation, and
  the cross-rung propagation logic.

- **CLI output is JSON and Markdown.** The CLI ratchet produces JSON files
  and Markdown lessons. For interactive exploration, use the Plan C dashboard
  notebook (`plan_c/00_dashboard.ipynb`), which provides a widget-based
  interface for running experiments and viewing results.

- **It does not parallelise evaluations.** Each experiment runs sequentially.
  On a machine with multiple cores, you could shard the challenger set across
  processes, but that is not implemented.


---


## Part 9: Architecture diagram

```
                          configs/rungs/rung1-5.yaml
                                    |
                                    v
                          +---------+---------+
                          |   AutoresearchHarness   |
                          |   (ratchet/runner.py)    |
                          +---+-----+-----+---+
                              |     |     |
                 +------------+     |     +------------+
                 |                  |                   |
                 v                  v                   v
         CompositeGenerator    LocalCheapExecutor   ResearchStore
        (search/strategies.py) (execution/local.py) (persistence/store.py)
                 |                  |                   |
      +----------+------+          |          +--------+--------+
      |          |      |          |          |        |        |
      v          v      v          v          v        v        v
  Neighbor  Random  Lesson    build_circuit  save_   save_    save_
  Walk      Combo   Guided    _bundle()      exp     step     progress
                      |            |
                      v            v
              LessonFeedback   AerSimulator
             (lessons/          + noise model
              feedback.py)      + postselection
                                + witness
                                + scoring
```

The data flows in a circle:

```
  Evaluate --> Score --> Compare --> Learn --> Narrow --> Generate --> Evaluate
```

That circle is the ratchet step. Each rung runs it multiple times. Each
ratchet runs multiple rungs. The lessons tighten the circle with every pass.


---

*This document was last updated on 2026-04-16 to describe the system as
built. The code is the ground truth. If this document contradicts the code,
the code is correct.*
