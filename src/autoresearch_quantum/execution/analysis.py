from __future__ import annotations

from collections import Counter
from math import sqrt
from statistics import fmean, pstdev
from typing import Any, Iterable


def local_memory_records(memory: list[str], creg_names: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    ordered_names = list(reversed(creg_names))
    for shot in memory:
        parts = shot.split(" ")
        records.append(dict(zip(ordered_names, parts, strict=True)))
    return records


def sampler_memory_records(bitstrings_by_register: dict[str, list[str]]) -> list[dict[str, str]]:
    first_key = next(iter(bitstrings_by_register), None)
    if first_key is None:
        return []
    shots = len(bitstrings_by_register[first_key])
    records: list[dict[str, str]] = []
    for shot_index in range(shots):
        records.append(
            {name: bitstrings[shot_index] for name, bitstrings in bitstrings_by_register.items()}
        )
    return records


def syndrome_outcomes(syndrome_bits: str, syndrome_labels: list[str]) -> dict[str, int]:
    if not syndrome_labels:
        return {}
    least_significant_first = syndrome_bits[::-1]
    return {
        label: int(bit)
        for label, bit in zip(syndrome_labels, least_significant_first, strict=True)
    }


def postselection_passes(postselection: str, syndrome_labels: list[str], syndrome_bits: str) -> bool:
    if postselection == "none" or not syndrome_labels:
        return True
    outcomes = syndrome_outcomes(syndrome_bits, syndrome_labels)
    if postselection == "all_measured":
        return all(bit == 0 for bit in outcomes.values())
    if postselection == "z_only":
        return outcomes.get("z_stabilizer", 0) == 0
    if postselection == "x_only":
        return outcomes.get("x_stabilizer", 0) == 0
    raise ValueError(f"Unsupported postselection rule: {postselection}")


def operator_eigenvalue(data_bits: str, measured_qubits: Iterable[int]) -> int:
    least_significant_first = data_bits[::-1]
    parity = sum(least_significant_first[index] == "1" for index in measured_qubits)
    return 1 if parity % 2 == 0 else -1


def summarize_context(
    records: list[dict[str, str]],
    syndrome_labels: list[str],
    postselection: str,
    operator: dict[int, str] | None = None,
) -> dict[str, Any]:
    total_shots = len(records)
    syndrome_counter: Counter[str] = Counter()
    raw_data_counter: Counter[str] = Counter()
    accepted_counter: Counter[str] = Counter()
    accepted_values: list[int] = []
    accepted = 0

    for shot in records:
        syndrome_bits = shot.get("syndrome", "")
        data_bits = shot.get("readout", "")
        syndrome_counter[syndrome_bits] += 1
        raw_data_counter[data_bits] += 1
        passes = postselection_passes(postselection, syndrome_labels, syndrome_bits)
        if not passes:
            continue
        accepted += 1
        accepted_counter[data_bits] += 1
        if operator is not None:
            accepted_values.append(operator_eigenvalue(data_bits, operator.keys()))

    acceptance_rate = accepted / total_shots if total_shots else 0.0
    expectation = (
        sum(accepted_values) / len(accepted_values)
        if accepted_values
        else 0.0
    )
    return {
        "total_shots": total_shots,
        "accepted_shots": accepted,
        "acceptance_rate": acceptance_rate,
        "expectation": expectation,
        "syndrome_counts": dict(syndrome_counter),
        "raw_data_counts": dict(raw_data_counter),
        "accepted_data_counts": dict(accepted_counter),
    }


def logical_magic_witness(logical_x: float, logical_y: float, spectator_z: float) -> float:
    witness = (1.0 + ((logical_x + logical_y) / sqrt(2.0))) / 2.0
    spectator_alignment = (1.0 + spectator_z) / 2.0
    value = witness * spectator_alignment
    return max(0.0, min(1.0, value))


def stability_score(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return 1.0
    mean_value = fmean(values)
    if abs(mean_value) < 1e-9:
        return 0.0
    variation = pstdev(values)
    return max(0.0, min(1.0, 1.0 - (variation / max(abs(mean_value), 1e-9))))
