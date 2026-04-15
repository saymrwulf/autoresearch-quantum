"""Tests for CLI parsing and override logic."""
from __future__ import annotations

import pytest

from autoresearch_quantum.cli import _parse_override, build_parser

# ── _parse_override ──────────────────────────────────────────────────────────

def test_parse_override_bool_true() -> None:
    assert _parse_override("flag=true") == ("flag", True)


def test_parse_override_bool_false() -> None:
    assert _parse_override("flag=false") == ("flag", False)


def test_parse_override_int() -> None:
    assert _parse_override("shots=1024") == ("shots", 1024)


def test_parse_override_negative_int() -> None:
    assert _parse_override("offset=-5") == ("offset", -5)


def test_parse_override_float() -> None:
    key, val = _parse_override("rate=0.95")
    assert key == "rate"
    assert abs(val - 0.95) < 1e-9


def test_parse_override_json_list() -> None:
    key, val = _parse_override("initial_layout=[0,1,2,3]")
    assert key == "initial_layout"
    assert val == [0, 1, 2, 3]


def test_parse_override_string() -> None:
    assert _parse_override("name=hello_world") == ("name", "hello_world")


def test_parse_override_empty_value() -> None:
    assert _parse_override("name=") == ("name", "")


def test_parse_override_no_equals_raises() -> None:
    with pytest.raises(ValueError, match="key=value"):
        _parse_override("no_equals_here")


# ── build_parser ─────────────────────────────────────────────────────────────

def test_parser_run_experiment_args() -> None:
    parser = build_parser()
    args = parser.parse_args(["run-experiment", "--config", "configs/rungs/rung1.yaml"])
    assert args.command == "run-experiment"
    assert args.config == "configs/rungs/rung1.yaml"


def test_parser_run_ratchet_multiple_configs() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "run-ratchet",
        "--config", "configs/rungs/rung1.yaml",
        "--config", "configs/rungs/rung2.yaml",
    ])
    assert args.command == "run-ratchet"
    assert len(args.config) == 2


def test_parser_run_transfer_with_backends() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "run-transfer",
        "--config", "configs/rungs/rung1.yaml",
        "--backends", "fake_brisbane", "fake_kyoto",
    ])
    assert args.backends == ["fake_brisbane", "fake_kyoto"]


def test_parser_requires_command() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
