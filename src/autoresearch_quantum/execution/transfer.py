from __future__ import annotations

import logging
from dataclasses import replace
from statistics import fmean, stdev

from ..models import ExperimentSpec, RungConfig, TransferReport
from .local import LocalCheapExecutor

logger = logging.getLogger(__name__)


class TransferEvaluator:
    """Evaluate a single spec across multiple backend noise models.

    The transfer_score is the minimum across backends (pessimistic),
    which prevents overfitting to a single noise profile.
    """

    def __init__(self, executor: LocalCheapExecutor | None = None) -> None:
        self.executor = executor or LocalCheapExecutor()

    def evaluate_across_backends(
        self,
        spec: ExperimentSpec,
        backends: list[str],
        rung_config: RungConfig,
    ) -> TransferReport:
        per_backend_scores: dict[str, float] = {}
        per_backend_metrics = {}

        for backend_name in backends:
            backend_spec = spec.with_updates(
                target_backend=backend_name,
                noise_backend=backend_name,
            )
            result = self.executor.evaluate(backend_spec, rung_config)
            per_backend_scores[backend_name] = result.score
            per_backend_metrics[backend_name] = result.metrics
            logger.info(
                "Transfer eval: spec %s on %s -> score %.4f",
                spec.fingerprint(),
                backend_name,
                result.score,
            )

        scores = list(per_backend_scores.values())
        mean_s = fmean(scores)
        min_s = min(scores)
        max_s = max(scores)
        std_s = stdev(scores) if len(scores) > 1 else 0.0

        return TransferReport(
            spec=spec,
            per_backend_scores=per_backend_scores,
            per_backend_metrics=per_backend_metrics,
            mean_score=mean_s,
            min_score=min_s,
            max_score=max_s,
            std_score=std_s,
            transfer_score=min_s,  # pessimistic
        )
