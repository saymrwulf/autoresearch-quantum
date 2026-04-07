from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .config import load_rung_config
from .models import ExperimentSpec
from .persistence.store import ResearchStore
from .ratchet.runner import AutoresearchHarness


def _parse_override(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise ValueError(f"Override must be in key=value format, got: {value!r}")
    key, raw = value.split("=", 1)
    if raw.lower() in {"true", "false"}:
        return key, raw.lower() == "true"
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return key, int(raw)
    try:
        return key, float(raw)
    except ValueError:
        pass
    if raw.startswith("[") and raw.endswith("]"):
        return key, json.loads(raw)
    return key, raw


def _build_spec_from_config(config_path: Path, overrides: list[str]) -> tuple[Any, ExperimentSpec]:
    rung_config = load_rung_config(config_path)
    spec = rung_config.bootstrap_incumbent
    update_payload = dict(_parse_override(item) for item in overrides)
    if update_payload:
        spec = spec.with_updates(**update_payload)
    return rung_config, spec


def _print_json(payload: Any) -> None:
    def _default(value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        return str(value)

    print(json.dumps(payload, indent=2, default=_default))


def _add_store_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store-dir", default="data/default", help="Persistent result store directory.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quantum autoresearch ratchet CLI")
    _add_store_arg(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    experiment = subparsers.add_parser("run-experiment", help="Run one local experiment.")
    _add_store_arg(experiment)
    experiment.add_argument("--config", required=True)
    experiment.add_argument("--set", action="append", default=[], help="Override spec fields: key=value")
    experiment.add_argument("--hardware", action="store_true", help="Also run hardware confirmation if enabled.")

    challenger_set = subparsers.add_parser("run-challenger-set", help="Evaluate one challenger neighborhood.")
    _add_store_arg(challenger_set)
    challenger_set.add_argument("--config", required=True)

    step = subparsers.add_parser("run-step", help="Run one ratchet step.")
    _add_store_arg(step)
    step.add_argument("--config", required=True)
    step.add_argument("--hardware", action="store_true")

    rung = subparsers.add_parser("run-rung", help="Run a full rung.")
    _add_store_arg(rung)
    rung.add_argument("--config", required=True)
    rung.add_argument("--hardware", action="store_true")

    ratchet = subparsers.add_parser("run-ratchet", help="Run multiple rung configs in order.")
    _add_store_arg(ratchet)
    ratchet.add_argument("--config", action="append", required=True)
    ratchet.add_argument("--hardware", action="store_true")

    transfer = subparsers.add_parser("run-transfer", help="Evaluate a spec across multiple backends.")
    _add_store_arg(transfer)
    transfer.add_argument("--config", required=True)
    transfer.add_argument("--set", action="append", default=[], help="Override spec fields: key=value")
    transfer.add_argument("--backends", nargs="+", help="Backend names to evaluate on (overrides config).")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    store = ResearchStore(args.store_dir)
    harness = AutoresearchHarness(store)

    if args.command == "run-experiment":
        rung_config, spec = _build_spec_from_config(Path(args.config), args.set)
        record = harness.run_single_experiment(
            spec,
            rung_config,
            promote_to_hardware=bool(args.hardware),
        )
        _print_json(
            {
                "experiment_id": record.experiment_id,
                "score": record.final_score,
                "cheap_score": record.cheap_result.score,
                "expensive_score": record.expensive_result.score if record.expensive_result else None,
                "failure_mode": record.best_result.metrics.dominant_failure_mode,
            }
        )
        return 0

    if args.command == "run-challenger-set":
        rung_config = load_rung_config(args.config)
        records = harness.run_challenger_set(rung_config)
        _print_json(
            [
                {
                    "experiment_id": record.experiment_id,
                    "mutation": record.mutation_note,
                    "cheap_score": record.cheap_result.score,
                }
                for record in records
            ]
        )
        return 0

    if args.command == "run-step":
        rung_config = load_rung_config(args.config)
        step = harness.run_ratchet_step(rung_config, allow_hardware=bool(args.hardware))
        _print_json(step)
        return 0

    if args.command == "run-rung":
        rung_config = load_rung_config(args.config)
        steps, lesson, feedback = harness.run_rung(rung_config, allow_hardware=bool(args.hardware))
        _print_json({
            "steps": steps,
            "lesson_path": str(store.rung_dir(rung_config.rung) / "lesson.md"),
            "lesson": lesson,
            "feedback_rules": len(feedback.rules),
            "narrowed_dimensions": feedback.narrowed_dimensions,
        })
        return 0

    if args.command == "run-ratchet":
        configs = [load_rung_config(path) for path in args.config]
        results = harness.run_ratchet(configs, allow_hardware=bool(args.hardware))
        _print_json([
            {
                "rung": lesson.rung,
                "lesson": lesson,
                "feedback_rules": len(feedback.rules),
            }
            for lesson, feedback in results
        ])
        return 0

    if args.command == "run-transfer":
        from .execution.transfer import TransferEvaluator
        rung_config, spec = _build_spec_from_config(Path(args.config), getattr(args, "set", []))
        backends = args.backends or rung_config.transfer_backends
        if not backends:
            print("Error: No backends specified. Use --backends or add transfer_backends to config.")
            return 1
        evaluator = TransferEvaluator(harness.local_executor)
        report = evaluator.evaluate_across_backends(spec, backends, rung_config)
        _print_json({
            "spec_fingerprint": spec.fingerprint(),
            "transfer_score": report.transfer_score,
            "mean_score": report.mean_score,
            "min_score": report.min_score,
            "max_score": report.max_score,
            "std_score": report.std_score,
            "per_backend_scores": report.per_backend_scores,
        })
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
