"""Autoresearch harness for encoded magic-state preparation."""

from .config import load_rung_config
from .models import ExperimentSpec

__all__ = ["ExperimentSpec", "load_rung_config"]
