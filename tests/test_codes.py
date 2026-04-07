"""Tests for codes.four_two_two — all seed and encoder styles."""
from __future__ import annotations

from math import pi

import pytest
from qiskit.quantum_info import Statevector

from autoresearch_quantum.codes.four_two_two import (
    STABILIZERS,
    apply_magic_seed,
    build_encoder,
    build_preparation_circuit,
    encoded_magic_statevector,
)
from qiskit import QuantumCircuit


# ── apply_magic_seed ─────────────────────────────────────────────────────────

def test_magic_seed_h_p() -> None:
    qc = QuantumCircuit(1)
    apply_magic_seed(qc, 0, "h_p")
    sv = Statevector.from_instruction(qc)
    assert abs(sv.probabilities().sum() - 1.0) < 1e-9


def test_magic_seed_ry_rz() -> None:
    qc = QuantumCircuit(1)
    apply_magic_seed(qc, 0, "ry_rz")
    sv = Statevector.from_instruction(qc)
    assert abs(sv.probabilities().sum() - 1.0) < 1e-9


def test_magic_seed_u_magic() -> None:
    qc = QuantumCircuit(1)
    apply_magic_seed(qc, 0, "u_magic")
    sv = Statevector.from_instruction(qc)
    assert abs(sv.probabilities().sum() - 1.0) < 1e-9


def test_magic_seed_all_styles_equivalent() -> None:
    """All seed styles should produce the same single-qubit state (up to global phase)."""
    states = []
    for style in ["h_p", "ry_rz", "u_magic"]:
        qc = QuantumCircuit(1)
        apply_magic_seed(qc, 0, style)
        states.append(Statevector.from_instruction(qc))
    # Check fidelity between pairs
    from qiskit.quantum_info import state_fidelity
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            fid = state_fidelity(states[i], states[j])
            assert fid == pytest.approx(1.0, abs=1e-6), (
                f"Seed styles produced different states: fidelity={fid}"
            )


def test_magic_seed_unsupported_raises() -> None:
    qc = QuantumCircuit(1)
    with pytest.raises(ValueError, match="Unsupported seed style"):
        apply_magic_seed(qc, 0, "unknown_style")


# ── build_encoder ────────────────────────────────────────────────────────────

def test_encoder_cx_chain() -> None:
    enc = build_encoder("cx_chain")
    assert enc.num_qubits == 4


def test_encoder_cz_compiled() -> None:
    enc = build_encoder("cz_compiled")
    assert enc.num_qubits == 4


def test_encoder_styles_equivalent() -> None:
    """Both encoder styles should produce equivalent encoded states."""
    from qiskit.quantum_info import state_fidelity
    sv_cx = Statevector.from_instruction(build_preparation_circuit("h_p", "cx_chain"))
    sv_cz = Statevector.from_instruction(build_preparation_circuit("h_p", "cz_compiled"))
    fid = state_fidelity(sv_cx, sv_cz)
    assert fid == pytest.approx(1.0, abs=1e-6)


def test_encoder_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported encoder style"):
        build_encoder("unknown_encoder")


# ── Stabilizer checks for all style combos ───────────────────────────────────

@pytest.mark.parametrize("seed,encoder", [
    ("h_p", "cx_chain"),
    ("h_p", "cz_compiled"),
    ("ry_rz", "cx_chain"),
    ("ry_rz", "cz_compiled"),
    ("u_magic", "cx_chain"),
    ("u_magic", "cz_compiled"),
])
def test_all_style_combos_satisfy_stabilizers(seed: str, encoder: str) -> None:
    state = Statevector.from_instruction(build_preparation_circuit(seed, encoder))
    for name, stab in STABILIZERS.items():
        exp = state.expectation_value(stab)
        assert abs(exp - 1.0) < 1e-6, (
            f"Stabilizer {name} failed for seed={seed}, encoder={encoder}: exp={exp}"
        )
