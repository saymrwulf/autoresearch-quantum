from __future__ import annotations

from math import pi

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector


DATA_QUBITS = 4
MAGIC_PREP_QUBIT = 0
SPECTATOR_LOGICAL_QUBIT = 1
STABILIZERS = {
    "z_stabilizer": SparsePauliOp.from_list([("ZZZZ", 1.0)]),
    "x_stabilizer": SparsePauliOp.from_list([("XXXX", 1.0)]),
}
MEASUREMENT_OPERATORS = {
    "logical_x": {0: "X", 2: "X"},
    "logical_y": {0: "Y", 1: "Z", 2: "X"},
    "spectator_z": {1: "Z", 2: "Z"},
}


def apply_magic_seed(circuit: QuantumCircuit, qubit: int, style: str) -> None:
    if style == "h_p":
        circuit.h(qubit)
        circuit.p(pi / 4, qubit)
        return
    if style == "ry_rz":
        circuit.ry(pi / 2, qubit)
        circuit.rz(pi / 4, qubit)
        return
    if style == "u_magic":
        circuit.u(pi / 2, 0.0, pi / 4, qubit)
        return
    raise ValueError(f"Unsupported seed style: {style}")


def build_encoder(style: str = "cx_chain") -> QuantumCircuit:
    circuit = QuantumCircuit(DATA_QUBITS, name=f"encoder_{style}")
    if style == "cx_chain":
        circuit.cx(0, 2)
        circuit.cx(1, 0)
        circuit.h(3)
        circuit.cx(3, 0)
        circuit.cx(3, 1)
        circuit.cx(3, 2)
        return circuit
    if style == "cz_compiled":
        circuit.h(2)
        circuit.cz(0, 2)
        circuit.h(2)
        circuit.h(0)
        circuit.cz(1, 0)
        circuit.h(0)
        circuit.h(3)
        circuit.h(0)
        circuit.cz(3, 0)
        circuit.h(0)
        circuit.h(1)
        circuit.cz(3, 1)
        circuit.h(1)
        circuit.h(2)
        circuit.cz(3, 2)
        circuit.h(2)
        return circuit
    raise ValueError(f"Unsupported encoder style: {style}")


def build_preparation_circuit(seed_style: str = "h_p", encoder_style: str = "cx_chain") -> QuantumCircuit:
    circuit = QuantumCircuit(DATA_QUBITS, name="prep_422_magic")
    apply_magic_seed(circuit, MAGIC_PREP_QUBIT, seed_style)
    circuit.compose(build_encoder(encoder_style), qubits=range(DATA_QUBITS), inplace=True)
    return circuit


def encoded_magic_statevector() -> Statevector:
    return Statevector.from_instruction(build_preparation_circuit())

