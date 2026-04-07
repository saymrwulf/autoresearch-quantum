"""Teaching toolkit — widget-based active learning and progress tracking."""

from autoresearch_quantum.teaching.tracker import LearningTracker
from autoresearch_quantum.teaching.assess import (
    quiz,
    predict_choice,
    reflect,
    order,
    checkpoint_summary,
    # Legacy aliases for backwards compatibility
    multiple_choice,
    predict,
    check_prediction,
    numerical_answer,
    free_response,
    code_challenge,
    concept_sort,
)

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
