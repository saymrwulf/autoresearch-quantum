# Autoresearch Quantum

`autoresearch-quantum` is a Python research harness for a Karpathy-style autoresearch ratchet in quantum experiments:

- keep an incumbent experiment
- generate challenger experiments
- screen challengers on a cheap tier
- promote only justified challengers to an expensive tier
- replace the incumbent only when the challenger wins on the final criterion
- log every ratchet step
- extract a transferable lesson at the end of each rung

The first built-in experiment family targets encoded magic-state preparation in the `[[4,2,2]]` code with Qiskit. The framework is designed so the `[[4,2,2]]` rung is not the destination. It is the first rung in a ladder that shifts from best-circuit hunting toward reusable design rules for larger encoded workflows.

## Project Tree

```text
autoresearch-quantum/
├── configs/rungs/
│   ├── rung1.yaml          Baseline: what recipe works?
│   ├── rung2.yaml          Stability under noise variation
│   ├── rung3.yaml          Transfer across backends
│   ├── rung4.yaml          Factory throughput / cost
│   └── rung5.yaml          Rosenfeld direction
├── src/autoresearch_quantum/
│   ├── cli.py              CLI entry point
│   ├── config.py           YAML config loader
│   ├── models.py           All data structures
│   ├── codes/
│   │   └── four_two_two.py [[4,2,2]] stabilisers, encoder, seed gates
│   ├── experiments/
│   │   └── encoded_magic_state.py  Circuit bundle builder
│   ├── execution/
│   │   ├── analysis.py     Postselection, witness, stability
│   │   ├── backends.py     Backend resolution
│   │   ├── hardware.py     IBM hardware executor
│   │   ├── local.py        Aer noise simulation executor
│   │   ├── transfer.py     Cross-backend transfer evaluator
│   │   └── transpile.py    Transpilation utilities
│   ├── lessons/
│   │   ├── extractor.py    Human-readable lesson extraction
│   │   └── feedback.py     Machine-readable rules + search narrowing
│   ├── persistence/
│   │   └── store.py        JSON file store with resumability
│   ├── ratchet/
│   │   └── runner.py       AutoresearchHarness orchestrator
│   ├── scoring/
│   │   └── score.py        WAC + factory throughput scorers
│   ├── search/
│   │   ├── challengers.py  Neighbour generation with dedup
│   │   └── strategies.py   NeighborWalk, RandomCombo, LessonGuided
│   └── teaching/
│       ├── assess.py       Widget-based quizzes, predictions, reflections
│       └── tracker.py      LearningTracker — per-student progress tracking
├── paper/
│   ├── autoresearch_quantum.tex   Full technical paper (LaTeX)
│   ├── autoresearch_quantum.pdf   Compiled PDF (19 pages)
│   ├── compendium.tex             Companion textbook (LaTeX)
│   └── compendium.pdf             Compiled PDF (36 pages)
├── notebooks/
│   ├── plan_a/              Bottom-up: 3 sequential notebooks
│   │   ├── 01_encoded_magic_state.ipynb
│   │   ├── 02_measuring_progress.ipynb
│   │   └── 03_the_ratchet.ipynb
│   ├── plan_b/              Spiral: 1 notebook, three passes
│   │   └── spiral_notebook.ipynb
│   ├── plan_c/              Parallel tracks + dashboard
│   │   ├── 00_dashboard.ipynb
│   │   ├── track_a_physics.ipynb
│   │   ├── track_b_engineering.ipynb
│   │   └── track_c_search.ipynb
│   └── plan_d/              Three claim-driven experiments
│       ├── experiment_1_protection.ipynb
│       ├── experiment_2_noise.ipynb
│       └── experiment_3_optimisation.ipynb
├── tests/                   107 tests
│   ├── test_analysis.py
│   ├── test_cli.py
│   ├── test_codes.py
│   ├── test_config.py
│   ├── test_experiments.py
│   ├── test_feedback.py
│   ├── test_harness.py
│   ├── test_persistence.py
│   └── test_scoring.py
├── THE_STORY.md             Narrative documentation
├── pyproject.toml
└── README.md
```

## Scientific Framing

### What is optimized

The harness optimizes an **experiment**, not just a circuit. A spec includes:

- logical magic-seed construction
- encoder realization
- verification strategy
- postselection rule
- ancilla strategy
- transpilation choices
- backend target and noise proxy
- shot and repeat allocation

### What is measured

The default score is:

```text
score = (usable_magic_quality * acceptance_rate) / total_cost
```

with a configurable `usable_magic_quality` assembled from:

- noisy encoded fidelity proxy
- logical magic witness
- codespace survival / postselection success
- stability under repeated noisy evaluation
- spectator logical alignment

and a configurable `total_cost` assembled from:

- two-qubit gate count
- transpiled depth
- total shots consumed
- runtime proxy
- hardware queue proxy

### Cheap tier vs expensive tier

Cheap tier:

- backend-aware transpilation
- noisy Aer evaluation
- density-matrix fidelity when a backend-derived noise model is available
- repeated local runs for stability scoring

Expensive tier:

- IBM Runtime execution through `SamplerV2`
- only used when enabled and when cheap-tier promotion thresholds are met
- isolated behind [`hardware.py`](src/autoresearch_quantum/execution/hardware.py)

## Built-In `[[4,2,2]]` Experiment

The built-in experiment prepares an encoded logical T-state on one logical qubit of the `[[4,2,2]]` code while keeping the spectator logical qubit in `|0⟩`. The code utilities live in [`four_two_two.py`](src/autoresearch_quantum/codes/four_two_two.py).

The harness evaluates:

- acceptance under optional `ZZZZ` and `XXXX` stabilizer checks
- logical `X` and `Y` witnesses for the encoded magic state
- spectator logical `Z`
- compiled cost after transpilation to a chosen backend target

This keeps the core scientific distinction explicit:

- a circuit can be locally good for `[[4,2,2]]`
- a rule is only valuable if it keeps helping across new backends or new rungs

## Installation

Create an isolated environment in the project root and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,notebooks]'
```

For the optional IBM hardware path:

```bash
pip install -e '.[hardware,dev,notebooks]'
```

If you want the CLI without installing editable mode, use `PYTHONPATH=src`.

## Jupyter Notebooks --- Learning Plans

The `notebooks/` folder contains four independent learning experiences.
Each plan teaches the same material (encoded magic-state preparation, measurement, and the ratchet optimiser) through a different didactic lens.
**No IBM account or API key is needed** --- everything runs locally with the Aer simulator.

### Quick start

```bash
# 1. Activate the virtual environment (if not already active)
. .venv/bin/activate

# 2. Install the project with notebook dependencies
pip install -e '.[notebooks]'

# 3. Start the Jupyter server
jupyter lab --notebook-dir=notebooks
```

This opens JupyterLab in your browser (usually at http://localhost:8888).
Navigate into any plan folder and open the first notebook.

> **Alternative:** If you prefer the classic notebook interface, run
> `jupyter notebook --notebook-dir=notebooks` instead.

### Plan A --- Bottom-Up (3 sequential notebooks)

| # | File | What you learn |
|---|------|----------------|
| 1 | `plan_a/01_encoded_magic_state.ipynb` | T-state, [[4,2,2]] encoder, stabilisers, error detection, postselection |
| 2 | `plan_a/02_measuring_progress.ipynb` | Noise, logical operators, magic witness, scoring formula, parameter sweeps |
| 3 | `plan_a/03_the_ratchet.ipynb` | Incumbent/challenger model, ratchet steps, lessons, cross-rung propagation |

Start with notebook 01 and work through in order.
Run each cell top-to-bottom (Shift+Enter).

### Plan B --- Spiral (1 notebook, three passes)

| File | What you learn |
|------|----------------|
| `plan_b/spiral_notebook.ipynb` | **Pass 1:** 5-min demo (black-box). **Pass 2:** Open the box (circuits, stabilisers, scoring). **Pass 3:** Make it your own (modify parameters, run experiments). |

One notebook, 78 cells. Each pass revisits the same system at a deeper level.

### Plan C --- Parallel Tracks (4 notebooks)

| File | Focus |
|------|-------|
| `plan_c/00_dashboard.ipynb` | Interactive dashboard (ipywidgets) --- run experiments from dropdowns |
| `plan_c/track_a_physics.ipynb` | Pure quantum mechanics: Eastin-Knill, Bloch sphere, stabiliser algebra |
| `plan_c/track_b_engineering.ipynb` | Noise models, transpilation, cost model, failure modes |
| `plan_c/track_c_search.ipynb` | Parameter space, search strategies, lesson extraction, cross-rung transfer |

Start with the dashboard for an overview, then dive into whichever track interests you.
The three tracks are independent and can be read in any order.

### Plan D --- Three Claim-Driven Experiments

| # | File | Hypothesis |
|---|------|-----------|
| 1 | `plan_d/experiment_1_protection.ipynb` | The [[4,2,2]] code can protect a magic state: W=1.0, all errors detected |
| 2 | `plan_d/experiment_2_noise.ipynb` | Noise degrades quality but parameter choice matters >2× |
| 3 | `plan_d/experiment_3_optimisation.ipynb` | A ratchet can learn to optimise and its knowledge transfers |

Each notebook follows: **Hypothesis → Claim → Experiment → Proof → Next Hypothesis**.
The output of each experiment motivates the next.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: autoresearch_quantum` | Run `pip install -e '.[notebooks]'` inside the activated `.venv` |
| `ModuleNotFoundError: ipywidgets` | Run `pip install ipywidgets` --- needed for the Plan C dashboard |
| Plots don't render | Make sure `%matplotlib inline` is in the first code cell (it already is) |
| Kernel not found | In JupyterLab, select **Kernel > Change Kernel** and pick the `.venv` Python |

## How To Run

### 1. Run a single local experiment

Use the rung config bootstrap incumbent as-is:

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-experiment \
  --config configs/rungs/rung1.yaml \
  --store-dir data/demo
```

Override individual experiment fields:

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-experiment \
  --config configs/rungs/rung1.yaml \
  --store-dir data/demo \
  --set verification=z_only \
  --set postselection=z_only \
  --set ancilla_strategy=reused_single
```

### 2. Run one ratchet step

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-step \
  --config configs/rungs/rung1.yaml \
  --store-dir data/demo
```

This will:

- load or bootstrap the incumbent
- generate neighbor challengers from the rung search space
- evaluate every challenger on the cheap tier
- promote only margin-beating challengers if hardware is enabled
- log the step and update the incumbent pointer if a challenger wins

### 3. Run one full rung

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-rung \
  --config configs/rungs/rung1.yaml \
  --store-dir data/demo
```

Artifacts are persisted under `data/demo/rung_<n>/`:

- `experiments/*.json`
- `ratchet_steps/*.json`
- `incumbent.json`
- `lesson.json`
- `lesson.md`

### 4. Run a multi-rung ratchet campaign

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-ratchet \
  --config configs/rungs/rung1.yaml \
  --config configs/rungs/rung2.yaml \
  --config configs/rungs/rung3.yaml \
  --config configs/rungs/rung4.yaml \
  --store-dir data/campaign
```

### 5. Run an optional hardware-backed confirmation

First install the hardware extra and make IBM credentials available in the usual `qiskit-ibm-runtime` way. The simplest path is to export:

```bash
export QISKIT_IBM_TOKEN=...
```

Then enable the hardware tier in the rung config by setting `tier_policy.enable_hardware: true` and optionally `hardware.backend_name: ibm_brisbane`.

Run:

```bash
PYTHONPATH=src .venv/bin/python -m autoresearch_quantum run-step \
  --config configs/rungs/rung1.yaml \
  --store-dir data/hardware \
  --hardware
```

Only challengers that beat the incumbent cheap-tier score by `tier_policy.cheap_margin` are promoted.

## Extending The Ladder

The intended progression is:

1. `rung1.yaml`
   baseline `[[4,2,2]]` encoded magic-state preparation
2. `rung2.yaml`
   same code with stronger stability and backend-awareness
3. `rung3.yaml`
   transfer across backend families
4. `rung4.yaml`
   factory-style cost pressure

To add a new rung:

- create a new YAML in `configs/rungs/`
- narrow the challenger space to the specific next question
- tune cheap and expensive score weights for that rung
- keep the lesson document as the real product

To add a new experiment family:

- implement a new builder under `src/autoresearch_quantum/experiments/`
- define the target state, witness operators, verification flow, and logging metadata
- route the ratchet to that experiment family through config or a new CLI selector

## Notes On Interpretation

This harness is explicit about proxy vs confirmation:

- cheap-tier fidelity and witness numbers are local proxies
- hardware runs are scarce and should be treated as confirmation
- the most important artifact of each rung is the lesson, not just the incumbent ID

That is the intended ratchet: better experiment plus better search rule.
