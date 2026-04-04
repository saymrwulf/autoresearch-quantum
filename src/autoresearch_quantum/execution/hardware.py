from __future__ import annotations

from statistics import fmean

from ..codes.four_two_two import MEASUREMENT_OPERATORS
from ..experiments.encoded_magic_state import build_circuit_bundle
from ..models import EvaluationMetrics, ExperimentSpec, RungConfig, TierResult
from ..scoring.score import score_metrics
from .analysis import logical_magic_witness, sampler_memory_records, stability_score, summarize_context
from .backends import backend_metadata, resolve_backend
from .transpile import circuit_metadata, count_two_qubit_gates, runtime_estimate, transpile_circuits

try:
    from qiskit_ibm_runtime import SamplerV2
except ImportError:  # pragma: no cover - exercised only when hardware extras missing
    SamplerV2 = None


class IBMHardwareExecutor:
    def evaluate(self, spec: ExperimentSpec, rung_config: RungConfig) -> TierResult:
        if SamplerV2 is None:
            raise RuntimeError(
                "qiskit-ibm-runtime is not installed. Install the hardware extra to enable IBM execution."
            )

        backend_name = rung_config.hardware.backend_name or spec.target_backend
        backend = resolve_backend(backend_name, rung_config.hardware)
        bundle = build_circuit_bundle(spec)
        context_names = ["acceptance", *bundle.witness_circuits.keys()]
        raw_circuits = [bundle.acceptance, *bundle.witness_circuits.values()]
        transpiled_contexts = transpile_circuits(raw_circuits, spec, backend)
        circuits_by_name = dict(zip(context_names, transpiled_contexts, strict=True))

        shots = rung_config.tier_policy.expensive_shots
        repeats = rung_config.tier_policy.expensive_repeats
        sampler = SamplerV2(mode=backend)

        aggregate: dict[str, list[dict[str, object]]] = {name: [] for name in context_names}
        repeat_scores: list[float] = []
        notes: list[str] = []

        for _ in range(repeats):
            result = sampler.run(list(circuits_by_name.values()), shots=shots).result()
            for context_name, pub_result, circuit in zip(
                context_names,
                result,
                circuits_by_name.values(),
                strict=True,
            ):
                records = sampler_memory_records(
                    {
                        name: bit_array.get_bitstrings()
                        for name, bit_array in pub_result.data.items()
                    }
                )
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

        metrics = EvaluationMetrics(
            logical_magic_witness=logical_magic_witness(logical_x, logical_y, spectator_z),
            acceptance_rate=acceptance_rate,
            codespace_rate=fmean(
                float(item["acceptance_rate"])
                for summaries in aggregate.values()
                for item in summaries
            ),
            spectator_logical_z=spectator_z,
            logical_x=logical_x,
            logical_y=logical_y,
            stability_score=stability_score(repeat_scores),
            two_qubit_count=sum(count_two_qubit_gates(circuit) for circuit in circuits_by_name.values()),
            depth=max(circuit.depth() for circuit in circuits_by_name.values()),
            shot_count=shots * repeats * len(circuits_by_name),
            runtime_estimate=sum(runtime_estimate(circuit) for circuit in circuits_by_name.values()),
            queue_cost_proxy=1.0,
            transpile_metadata={
                name: circuit_metadata(circuit, spec) for name, circuit in circuits_by_name.items()
            },
            backend_metadata={"target_backend": backend_metadata(backend)},
        )
        metrics.dominant_failure_mode = (
            "hardware drift sensitivity"
            if (metrics.stability_score or 1.0) < 0.75
            else "hardware confirmation run"
        )

        score, quality, _ = score_metrics(metrics, "expensive", rung_config.score)
        notes.append(
            f"Hardware-tier confirmation used backend {backend.name} with {shots} shots x {repeats} repeats."
        )
        return TierResult(
            tier="expensive",
            score=score,
            quality_estimate=quality,
            metrics=metrics,
            counts_summary={
                name: {
                    "mean_acceptance_rate": fmean(float(item["acceptance_rate"]) for item in summaries),
                    "mean_expectation": fmean(float(item["expectation"]) for item in summaries),
                    "latest": summaries[-1],
                }
                for name, summaries in aggregate.items()
            },
            notes=notes,
        )
