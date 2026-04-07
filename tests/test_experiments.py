"""Tests for experiments.encoded_magic_state — circuit building edge cases."""
from __future__ import annotations

import pytest

from autoresearch_quantum.experiments.encoded_magic_state import (
    MeasurementCircuitBundle,
    _ancilla_count,
    _verification_checks,
    build_circuit_bundle,
)
from autoresearch_quantum.models import ExperimentSpec


def test_verification_none() -> None:
    spec = ExperimentSpec(rung=1, verification="none")
    assert _verification_checks(spec) == []


def test_verification_z_only() -> None:
    spec = ExperimentSpec(rung=1, verification="z_only")
    assert _verification_checks(spec) == ["z_stabilizer"]


def test_verification_x_only() -> None:
    spec = ExperimentSpec(rung=1, verification="x_only")
    assert _verification_checks(spec) == ["x_stabilizer"]


def test_verification_both() -> None:
    spec = ExperimentSpec(rung=1, verification="both")
    assert _verification_checks(spec) == ["z_stabilizer", "x_stabilizer"]


def test_verification_unsupported() -> None:
    spec = ExperimentSpec(rung=1, verification="quantum_magic")
    with pytest.raises(ValueError, match="Unsupported verification"):
        _verification_checks(spec)


def test_ancilla_dedicated_pair() -> None:
    spec = ExperimentSpec(rung=1, ancilla_strategy="dedicated_pair")
    assert _ancilla_count(spec, ["z_stabilizer", "x_stabilizer"]) == 2
    assert _ancilla_count(spec, ["z_stabilizer"]) == 1
    assert _ancilla_count(spec, []) == 0


def test_ancilla_reused_single() -> None:
    spec = ExperimentSpec(rung=1, ancilla_strategy="reused_single")
    assert _ancilla_count(spec, ["z_stabilizer", "x_stabilizer"]) == 1
    assert _ancilla_count(spec, []) == 0


def test_ancilla_unsupported() -> None:
    spec = ExperimentSpec(rung=1, ancilla_strategy="unknown")
    with pytest.raises(ValueError, match="Unsupported ancilla"):
        _ancilla_count(spec, ["z_stabilizer"])


def test_circuit_bundle_reused_single_ancilla() -> None:
    spec = ExperimentSpec(rung=1, ancilla_strategy="reused_single", verification="both")
    bundle = build_circuit_bundle(spec)
    assert isinstance(bundle, MeasurementCircuitBundle)
    for circ in bundle.witness_circuits.values():
        anc_regs = [r for r in circ.qregs if r.name == "anc"]
        assert len(anc_regs) == 1
        assert anc_regs[0].size == 1


def test_circuit_bundle_no_verification() -> None:
    spec = ExperimentSpec(rung=1, verification="none")
    bundle = build_circuit_bundle(spec)
    for circ in bundle.witness_circuits.values():
        assert circ.metadata["syndrome_labels"] == []
        anc_regs = [r for r in circ.qregs if r.name == "anc"]
        assert len(anc_regs) == 0
