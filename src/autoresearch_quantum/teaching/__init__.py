"""Teaching toolkit — widget-based active learning and progress tracking."""

from autoresearch_quantum.teaching.assess import (
    check_prediction,
    checkpoint_summary,
    code_challenge,
    concept_sort,
    free_response,
    # Legacy aliases for backwards compatibility
    multiple_choice,
    numerical_answer,
    order,
    predict,
    predict_choice,
    quiz,
    reflect,
)
from autoresearch_quantum.teaching.tracker import LearningTracker

__all__ = [
    "LearningTracker",
    "quiz",
    "predict_choice",
    "reflect",
    "order",
    "checkpoint_summary",
    # Legacy
    "multiple_choice",
    "predict",
    "check_prediction",
    "numerical_answer",
    "free_response",
    "code_challenge",
    "concept_sort",
]
