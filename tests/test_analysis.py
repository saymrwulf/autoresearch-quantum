"""Tests for execution.analysis — postselection modes, operator eigenvalues, stability."""
from __future__ import annotations

import pytest

from autoresearch_quantum.execution.analysis import (
    local_memory_records,
    logical_magic_witness,
    operator_eigenvalue,
    postselection_passes,
    sampler_memory_records,
    stability_score,
    summarize_context,
    syndrome_outcomes,
)


# ── local_memory_records ─────────────────────────────────────────────────────

def test_local_memory_records_splits_correctly() -> None:
    memory = ["00 0110", "01 1001"]
    records = local_memory_records(memory, ["readout", "syndrome"])
    # reversed creg order: ["syndrome", "readout"]
    assert records[0] == {"syndrome": "00", "readout": "0110"}
    assert records[1] == {"syndrome": "01", "readout": "1001"}


def test_local_memory_records_single_register() -> None:
    memory = ["0110"]
    records = local_memory_records(memory, ["readout"])
    assert records[0] == {"readout": "0110"}


# ── sampler_memory_records ───────────────────────────────────────────────────

def test_sampler_memory_records_basic() -> None:
    bitstrings = {
        "readout": ["0000", "1111"],
        "syndrome": ["00", "11"],
    }
    records = sampler_memory_records(bitstrings)
    assert len(records) == 2
    assert records[0] == {"readout": "0000", "syndrome": "00"}
    assert records[1] == {"readout": "1111", "syndrome": "11"}


def test_sampler_memory_records_empty() -> None:
    records = sampler_memory_records({})
    assert records == []


# ── syndrome_outcomes ────────────────────────────────────────────────────────

def test_syndrome_outcomes_two_stabilizers() -> None:
    # "10" as bits -> least_significant_first = "01"
    # z_stab gets bit '0' = 0, x_stab gets bit '1' = 1
    result = syndrome_outcomes("10", ["z_stabilizer", "x_stabilizer"])
    assert result == {"z_stabilizer": 0, "x_stabilizer": 1}


def test_syndrome_outcomes_empty_labels() -> None:
    assert syndrome_outcomes("10", []) == {}


# ── postselection_passes ────────────────────────────────────────────────────

def test_postselection_none_always_passes() -> None:
    assert postselection_passes("none", ["z_stabilizer"], "1") is True


def test_postselection_all_measured_passes_on_zeros() -> None:
    assert postselection_passes("all_measured", ["z_stabilizer", "x_stabilizer"], "00") is True


def test_postselection_all_measured_fails_on_nonzero() -> None:
    assert postselection_passes("all_measured", ["z_stabilizer", "x_stabilizer"], "01") is False


def test_postselection_z_only() -> None:
    # "01" reversed = "10", z_stabilizer = '1' = 1 -> fail
    assert postselection_passes("z_only", ["z_stabilizer", "x_stabilizer"], "01") is False
    # "10" reversed = "01", z_stabilizer = '0' = 0 -> pass
    assert postselection_passes("z_only", ["z_stabilizer", "x_stabilizer"], "10") is True


def test_postselection_x_only() -> None:
    # "01" reversed = "10", x_stabilizer = '0' = 0 -> pass
    assert postselection_passes("x_only", ["z_stabilizer", "x_stabilizer"], "01") is True
    # "10" reversed = "01", x_stabilizer = '1' = 1 -> fail
    assert postselection_passes("x_only", ["z_stabilizer", "x_stabilizer"], "10") is False


def test_postselection_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported postselection rule"):
        postselection_passes("unknown_mode", ["z_stabilizer"], "0")


# ── operator_eigenvalue ──────────────────────────────────────────────────────

def test_operator_eigenvalue_even_parity() -> None:
    assert operator_eigenvalue("0000", [0, 2]) == 1


def test_operator_eigenvalue_odd_parity() -> None:
    # "0100" reversed = "0010", bits at 0='0', 2='1' -> parity 1 -> -1
    assert operator_eigenvalue("0100", [0, 2]) == -1


# ── summarize_context ────────────────────────────────────────────────────────

def test_summarize_context_with_postselection() -> None:
    records = [
        {"syndrome": "00", "readout": "0000"},
        {"syndrome": "00", "readout": "0000"},
        {"syndrome": "01", "readout": "1111"},  # fails all_measured
    ]
    result = summarize_context(
        records,
        syndrome_labels=["z_stabilizer", "x_stabilizer"],
        postselection="all_measured",
    )
    assert result["total_shots"] == 3
    assert result["accepted_shots"] == 2
    assert abs(result["acceptance_rate"] - 2 / 3) < 1e-9


def test_summarize_context_no_postselection() -> None:
    records = [
        {"syndrome": "11", "readout": "0000"},
        {"syndrome": "11", "readout": "1111"},
    ]
    result = summarize_context(records, syndrome_labels=[], postselection="none")
    assert result["accepted_shots"] == 2


def test_summarize_context_with_operator() -> None:
    records = [
        {"syndrome": "00", "readout": "0000"},
        {"syndrome": "00", "readout": "0101"},
    ]
    result = summarize_context(
        records,
        syndrome_labels=["z_stabilizer", "x_stabilizer"],
        postselection="all_measured",
        operator={0: "X", 2: "X"},
    )
    assert "expectation" in result


def test_summarize_context_empty() -> None:
    result = summarize_context([], syndrome_labels=[], postselection="none")
    assert result["total_shots"] == 0
    assert result["acceptance_rate"] == 0.0


# ── logical_magic_witness ────────────────────────────────────────────────────

def test_logical_magic_witness_perfect() -> None:
    from math import sqrt
    # perfect values: logical_x=1/sqrt(2), logical_y=1/sqrt(2), spectator_z=1
    val = logical_magic_witness(1 / sqrt(2), 1 / sqrt(2), 1.0)
    assert 0.0 <= val <= 1.0
    assert val == pytest.approx(1.0, abs=1e-9)


def test_logical_magic_witness_clamped() -> None:
    val = logical_magic_witness(-10.0, -10.0, -1.0)
    assert val >= 0.0


# ── stability_score ──────────────────────────────────────────────────────────

def test_stability_score_empty() -> None:
    assert stability_score([]) == 0.0


def test_stability_score_single() -> None:
    assert stability_score([0.5]) == 1.0


def test_stability_score_identical_values() -> None:
    assert stability_score([0.5, 0.5, 0.5]) == 1.0


def test_stability_score_near_zero_mean() -> None:
    assert stability_score([0.0, 0.0]) == 0.0


def test_stability_score_high_variation() -> None:
    val = stability_score([0.1, 0.9])
    assert 0.0 <= val <= 1.0
