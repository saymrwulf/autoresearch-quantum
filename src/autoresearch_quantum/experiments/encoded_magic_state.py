from __future__ import annotations

from dataclasses import dataclass

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector

from ..codes.four_two_two import DATA_QUBITS, MEASUREMENT_OPERATORS, build_preparation_circuit
from ..models import ExperimentSpec


@dataclass(frozen=True)
class MeasurementCircuitBundle:
    prep: QuantumCircuit
    acceptance: QuantumCircuit
    witness_circuits: dict[str, QuantumCircuit]
    target_state: Statevector


def _verification_checks(spec: ExperimentSpec) -> list[str]:
    if spec.verification == "none":
        return []
    if spec.verification == "z_only":
        return ["z_stabilizer"]
    if spec.verification == "x_only":
        return ["x_stabilizer"]
    if spec.verification == "both":
        return ["z_stabilizer", "x_stabilizer"]
    raise ValueError(f"Unsupported verification mode: {spec.verification}")


def _ancilla_count(spec: ExperimentSpec, checks: list[str]) -> int:
    if not checks:
        return 0
    if spec.ancilla_strategy == "dedicated_pair":
        return len(checks)
    if spec.ancilla_strategy == "reused_single":
        return 1
    raise ValueError(f"Unsupported ancilla strategy: {spec.ancilla_strategy}")


def _add_z_check(circuit: QuantumCircuit, ancilla: int, data_qubits: list[int]) -> None:
    for qubit in data_qubits:
        circuit.cx(qubit, ancilla)


def _add_x_check(circuit: QuantumCircuit, ancilla: int, data_qubits: list[int]) -> None:
    circuit.h(ancilla)
    for qubit in data_qubits:
        circuit.cx(ancilla, qubit)
    circuit.h(ancilla)


def _measure_operator(circuit: QuantumCircuit, data_qubits: list[int], operator: dict[int, str]) -> None:
    for qubit in data_qubits:
        basis = operator.get(qubit, "Z")
        if basis == "X":
            circuit.h(qubit)
        elif basis == "Y":
            circuit.sdg(qubit)
            circuit.h(qubit)
        elif basis == "Z":
            continue
        else:
            raise ValueError(f"Unsupported basis: {basis}")


def _attach_verification(
    circuit: QuantumCircuit,
    spec: ExperimentSpec,
    data_qubits: list[int],
    ancilla_qubits: list[int],
    syndrome_bits: list[int],
) -> list[str]:
    checks = _verification_checks(spec)
    labels: list[str] = []
    if not checks:
        return labels

    if spec.ancilla_strategy == "dedicated_pair":
        for ancilla_qubit, syndrome_bit, label in zip(ancilla_qubits, syndrome_bits, checks, strict=True):
            if label == "z_stabilizer":
                _add_z_check(circuit, ancilla_qubit, data_qubits)
            else:
                _add_x_check(circuit, ancilla_qubit, data_qubits)
            circuit.measure(ancilla_qubit, syndrome_bit)
            labels.append(label)
        return labels

    ancilla_qubit = ancilla_qubits[0]
    for syndrome_bit, label in zip(syndrome_bits, checks, strict=True):
        if label == "z_stabilizer":
            _add_z_check(circuit, ancilla_qubit, data_qubits)
        else:
            _add_x_check(circuit, ancilla_qubit, data_qubits)
        circuit.measure(ancilla_qubit, syndrome_bit)
        labels.append(label)
        if label != checks[-1]:
            circuit.reset(ancilla_qubit)
    return labels


def _base_circuit(spec: ExperimentSpec, context_name: str, operator: dict[int, str] | None) -> QuantumCircuit:
    checks = _verification_checks(spec)
    ancilla_count = _ancilla_count(spec, checks)
    syndrome_bits = len(checks)

    data = QuantumRegister(DATA_QUBITS, "data")
    ancilla = QuantumRegister(ancilla_count, "anc") if ancilla_count else None
    syndrome = ClassicalRegister(syndrome_bits, "syndrome") if syndrome_bits else None
    readout = ClassicalRegister(DATA_QUBITS, "readout")

    registers = [data]
    if ancilla is not None:
        registers.append(ancilla)
    if syndrome is not None:
        registers.append(syndrome)
    registers.append(readout)

    circuit = QuantumCircuit(*registers, name=context_name)
    circuit.compose(
        build_preparation_circuit(spec.seed_style, spec.encoder_style),
        qubits=list(range(DATA_QUBITS)),
        inplace=True,
    )

    syndrome_labels: list[str] = []
    if ancilla is not None and syndrome is not None:
        syndrome_labels = _attach_verification(
            circuit,
            spec,
            data_qubits=list(range(DATA_QUBITS)),
            ancilla_qubits=list(range(DATA_QUBITS, DATA_QUBITS + ancilla_count)),
            syndrome_bits=list(range(syndrome_bits)),
        )

    if operator is not None:
        _measure_operator(circuit, list(range(DATA_QUBITS)), operator)

    circuit.measure(data, readout)
    circuit.metadata = {
        "context": context_name,
        "syndrome_labels": syndrome_labels,
        "postselection": spec.postselection,
        "logical_operator": operator,
    }
    return circuit


def build_circuit_bundle(spec: ExperimentSpec) -> MeasurementCircuitBundle:
    prep = build_preparation_circuit(spec.seed_style, spec.encoder_style)
    witness_circuits = {
        name: _base_circuit(spec, name, operator)
        for name, operator in MEASUREMENT_OPERATORS.items()
    }
    acceptance = _base_circuit(spec, "acceptance", operator=None)
    target_state = Statevector.from_instruction(build_preparation_circuit())
    return MeasurementCircuitBundle(
        prep=prep,
        acceptance=acceptance,
        witness_circuits=witness_circuits,
        target_state=target_state,
    )
