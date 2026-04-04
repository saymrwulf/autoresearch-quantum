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
├── configs/
│   └── rungs/
│       ├── rung1.yaml
│       ├── rung2.yaml
│       ├── rung3.yaml
│       └── rung4.yaml
├── src/
│   └── autoresearch_quantum/
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── codes/
│       │   └── four_two_two.py
│       ├── experiments/
│       │   └── encoded_magic_state.py
│       ├── execution/
│       │   ├── analysis.py
│       │   ├── backends.py
│       │   ├── hardware.py
│       │   ├── local.py
│       │   └── transpile.py
│       ├── lessons/
│       │   └── extractor.py
│       ├── persistence/
│       │   └── store.py
│       ├── ratchet/
│       │   └── runner.py
│       ├── scoring/
│       │   └── score.py
│       └── search/
│           └── challengers.py
├── tests/
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
- isolated behind [`hardware.py`](/Users/oho/GitClone/CodexProjects/autoresearch-quantum/src/autoresearch_quantum/execution/hardware.py)

## Built-In `[[4,2,2]]` Experiment

The built-in experiment prepares an encoded logical T-state on one logical qubit of the `[[4,2,2]]` code while keeping the spectator logical qubit in `|0⟩`. The code utilities live in [`four_two_two.py`](/Users/oho/GitClone/CodexProjects/autoresearch-quantum/src/autoresearch_quantum/codes/four_two_two.py).

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
pip install -e '.[dev]'
```

For the optional IBM hardware path:

```bash
pip install -e '.[hardware,dev]'
```

If you want the CLI without installing editable mode, use `PYTHONPATH=src`.

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
