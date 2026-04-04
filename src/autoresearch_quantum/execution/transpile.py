from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit.providers.backend import BackendV2

from ..models import ExperimentSpec


def transpile_circuits(
    circuits: list[QuantumCircuit],
    spec: ExperimentSpec,
    backend: BackendV2,
) -> list[QuantumCircuit]:
    transpiled = transpile(
        circuits,
        backend=backend,
        optimization_level=spec.optimization_level,
        layout_method=spec.layout_method,
        routing_method=spec.routing_method,
        approximation_degree=spec.approximation_degree,
        initial_layout=list(spec.initial_layout) if spec.initial_layout else None,
    )
    if isinstance(transpiled, QuantumCircuit):
        return [transpiled]
    return list(transpiled)


def count_two_qubit_gates(circuit: QuantumCircuit) -> int:
    return sum(1 for instruction in circuit.data if instruction.operation.num_qubits == 2)


def runtime_estimate(circuit: QuantumCircuit) -> float:
    resets = sum(1 for instruction in circuit.data if instruction.operation.name == "reset")
    return float(circuit.depth() + (3 * count_two_qubit_gates(circuit)) + (5 * resets))


def circuit_metadata(circuit: QuantumCircuit, spec: ExperimentSpec) -> dict[str, Any]:
    return {
        "optimization_level": spec.optimization_level,
        "layout_method": spec.layout_method,
        "routing_method": spec.routing_method,
        "approximation_degree": spec.approximation_degree,
        "depth": circuit.depth(),
        "size": circuit.size(),
        "two_qubit_count": count_two_qubit_gates(circuit),
    }
