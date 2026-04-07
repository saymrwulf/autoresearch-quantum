from __future__ import annotations

import hashlib
from math import fsum
from statistics import fmean

from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from ..codes.four_two_two import MEASUREMENT_OPERATORS
from ..experiments.encoded_magic_state import build_circuit_bundle
from ..models import EvaluationMetrics, ExperimentSpec, RungConfig, TierResult
from ..scoring.score import score_metrics
from .analysis import (
    local_memory_records,
    logical_magic_witness,
    stability_score,
    summarize_context,
)
from .backends import backend_metadata, resolve_backend
from .transpile import circuit_metadata, count_two_qubit_gates, runtime_estimate, transpile_circuits


def _dominant_failure_mode(metrics: EvaluationMetrics) -> str:
    if metrics.acceptance_rate < 0.45:
        return "postselection collapse"
    if metrics.logical_magic_witness is not None and metrics.logical_magic_witness < 0.65:
        return "logical witness erosion"
    if metrics.stability_score is not None and metrics.stability_score < 0.75:
        return "noise sensitivity"
    if metrics.two_qubit_count > 60 or metrics.depth > 120:
        return "transpile cost explosion"
    return "residual coherent/noisy error"


class LocalCheapExecutor:
    def evaluate(self, spec: ExperimentSpec, rung_config: RungConfig) -> TierResult:
        bundle = build_circuit_bundle(spec)
        target_backend = resolve_backend(spec.target_backend, rung_config.hardware)
        noise_backend_name = spec.noise_backend or spec.target_backend
        noise_backend = resolve_backend(noise_backend_name, rung_config.hardware)

        transpiled_prep = transpile_circuits([bundle.prep], spec, target_backend)[0]
        context_names = ["acceptance", *bundle.witness_circuits.keys()]
        raw_circuits = [bundle.acceptance, *bundle.witness_circuits.values()]
        transpiled_contexts = transpile_circuits(raw_circuits, spec, target_backend)
        circuits_by_name = dict(zip(context_names, transpiled_contexts, strict=True))

        ideal_fidelity = state_fidelity(Statevector.from_instruction(bundle.prep), bundle.target_state)
        noisy_fidelity = None
        shot_simulator: AerSimulator
        density_simulator: AerSimulator | None = None
        notes: list[str] = []

        try:
            noise_model = NoiseModel.from_backend(noise_backend)
            shot_simulator = AerSimulator(
                noise_model=noise_model,
                basis_gates=noise_model.basis_gates,
                coupling_map=getattr(noise_backend, "coupling_map", None),
            )
            density_simulator = AerSimulator(
                method="density_matrix",
                noise_model=noise_model,
                basis_gates=noise_model.basis_gates,
                coupling_map=getattr(noise_backend, "coupling_map", None),
            )
        except Exception as exc:  # pragma: no cover - depends on backend capabilities
            notes.append(f"Noise model unavailable, falling back to ideal simulation: {exc}")
            shot_simulator = AerSimulator()

        if density_simulator is not None:
            density_circuit = transpiled_prep.copy()
            density_circuit.save_density_matrix()
            density_result = density_simulator.run(density_circuit).result()
            noisy_density = density_result.data(0)["density_matrix"]
            noisy_fidelity = state_fidelity(noisy_density, bundle.target_state)

        repeats = spec.repeats or rung_config.tier_policy.cheap_repeats
        shots = spec.shots or rung_config.tier_policy.cheap_shots
        repeat_scores: list[float] = []
        aggregate: dict[str, list[dict[str, object]]] = {name: [] for name in context_names}

        for repeat_index in range(repeats):
            for context_name, circuit in circuits_by_name.items():
                result = shot_simulator.run(
                    circuit,
                    shots=shots,
                    memory=True,
                    seed_simulator=int(
                        hashlib.sha256(
                            f"{spec.fingerprint()}-{repeat_index}".encode()
                        ).hexdigest()[:8],
                        16,
                    ),
                ).result()
                memory = result.get_memory(circuit)
                records = local_memory_records(memory, [creg.name for creg in circuit.cregs])
                summary = summarize_context(
                    records,
                    syndrome_labels=list(circuit.metadata.get("syndrome_labels", [])),
                    postselection=str(circuit.metadata.get("postselection", "none")),
                    operator=MEASUREMENT_OPERATORS.get(context_name),
                )
                aggregate[context_name].append(summary)

            x_value = float(aggregate["logical_x"][-1]["expectation"])
            y_value = float(aggregate["logical_y"][-1]["expectation"])
            spectator = float(aggregate["spectator_z"][-1]["expectation"])
            acceptance = float(aggregate["acceptance"][-1]["acceptance_rate"])
            repeat_scores.append(logical_magic_witness(x_value, y_value, spectator) * acceptance)

        acceptance_rate = fmean(float(item["acceptance_rate"]) for item in aggregate["acceptance"])
        logical_x = fmean(float(item["expectation"]) for item in aggregate["logical_x"])
        logical_y = fmean(float(item["expectation"]) for item in aggregate["logical_y"])
        spectator_z = fmean(float(item["expectation"]) for item in aggregate["spectator_z"])
        witness = logical_magic_witness(logical_x, logical_y, spectator_z)
        codespace_rate = fmean(
            [
                float(item["acceptance_rate"])
                for summaries in aggregate.values()
                for item in summaries
            ]
        )

        total_two_qubit = sum(count_two_qubit_gates(circuit) for circuit in circuits_by_name.values())
        max_depth = max(circuit.depth() for circuit in circuits_by_name.values())
        total_runtime = fsum(runtime_estimate(circuit) for circuit in circuits_by_name.values())

        metrics = EvaluationMetrics(
            ideal_encoded_fidelity=ideal_fidelity,
            noisy_encoded_fidelity=noisy_fidelity if noisy_fidelity is not None else ideal_fidelity,
            logical_magic_witness=witness,
            acceptance_rate=acceptance_rate,
            codespace_rate=codespace_rate,
            spectator_logical_z=spectator_z,
            logical_x=logical_x,
            logical_y=logical_y,
            stability_score=stability_score(repeat_scores),
            two_qubit_count=total_two_qubit,
            depth=max_depth,
            shot_count=shots * repeats * len(circuits_by_name),
            runtime_estimate=total_runtime,
            queue_cost_proxy=0.0,
            transpile_metadata={
                name: circuit_metadata(circuit, spec) for name, circuit in circuits_by_name.items()
            },
            backend_metadata={
                "target_backend": backend_metadata(target_backend),
                "noise_backend": backend_metadata(noise_backend),
            },
        )
        metrics.dominant_failure_mode = _dominant_failure_mode(metrics)

        score, quality, _ = score_metrics(metrics, "cheap", rung_config.score)
        counts_summary = {
            name: {
                "mean_acceptance_rate": fmean(float(item["acceptance_rate"]) for item in summaries),
                "mean_expectation": fmean(float(item["expectation"]) for item in summaries),
                "latest": summaries[-1],
            }
            for name, summaries in aggregate.items()
        }
        notes.append(f"Cheap-tier proxy used {shots} shots x {repeats} repeats over {len(circuits_by_name)} circuits.")

        return TierResult(
            tier="cheap",
            score=score,
            quality_estimate=quality,
            metrics=metrics,
            counts_summary=counts_summary,
            notes=notes,
        )
