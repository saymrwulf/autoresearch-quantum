from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha1
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def short_hash(payload: str, length: int = 10) -> str:
    return sha1(payload.encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True)
class ExperimentSpec:
    rung: int
    seed_style: str = "h_p"
    encoder_style: str = "cx_chain"
    verification: str = "both"
    postselection: str = "all_measured"
    ancilla_strategy: str = "dedicated_pair"
    optimization_level: int = 2
    layout_method: str = "sabre"
    routing_method: str = "sabre"
    approximation_degree: float = 1.0
    target_backend: str = "fake_brisbane"
    noise_backend: str | None = None
    initial_layout: tuple[int, ...] | None = None
    shots: int = 2048
    repeats: int = 3
    notes: str = ""

    def with_updates(self, **changes: Any) -> ExperimentSpec:
        if "initial_layout" in changes and isinstance(changes["initial_layout"], list):
            changes["initial_layout"] = tuple(changes["initial_layout"])
        return replace(self, **changes)

    def identity_payload(self) -> str:
        payload = asdict(self)
        return repr(payload)

    def fingerprint(self) -> str:
        return short_hash(self.identity_payload())


@dataclass(frozen=True)
class QualityWeights:
    ideal_fidelity: float = 0.0
    noisy_fidelity: float = 0.0
    logical_witness: float = 0.0
    codespace_rate: float = 0.0
    stability_score: float = 0.0
    spectator_alignment: float = 0.0


@dataclass(frozen=True)
class CostWeights:
    two_qubit_count: float = 0.08
    depth: float = 0.01
    shot_count: float = 0.00015
    runtime_estimate: float = 0.02
    queue_cost_proxy: float = 0.3


@dataclass(frozen=True)
class ScoreConfig:
    name: str = "weighted_acceptance_cost"
    cheap_quality: QualityWeights = field(default_factory=QualityWeights)
    expensive_quality: QualityWeights = field(default_factory=QualityWeights)
    cost_weights: CostWeights = field(default_factory=CostWeights)
    base_cost: float = 1.0


@dataclass(frozen=True)
class SearchSpaceConfig:
    dimensions: dict[str, list[Any]] = field(default_factory=dict)
    max_challengers_per_step: int = 8


@dataclass(frozen=True)
class TierPolicyConfig:
    cheap_margin: float = 0.01
    confirmation_margin: float = 0.0
    cheap_shots: int = 2048
    expensive_shots: int = 4096
    cheap_repeats: int = 3
    expensive_repeats: int = 2
    noisy_simulator: str = "aer"
    promote_top_k: int = 2
    enable_hardware: bool = False
    confirm_incumbent_on_hardware: bool = True
    hardware_budget: int = 0


@dataclass(frozen=True)
class HardwareConfig:
    backend_name: str | None = None
    channel: str | None = None
    instance: str | None = None
    token_env_var: str = "QISKIT_IBM_TOKEN"


@dataclass(frozen=True)
class RungConfig:
    rung: int
    name: str
    description: str
    objective: str
    bootstrap_incumbent: ExperimentSpec
    search_space: SearchSpaceConfig
    tier_policy: TierPolicyConfig
    score: ScoreConfig
    step_budget: int = 3
    patience: int = 2
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    transfer_backends: list[str] = field(default_factory=list)


@dataclass
class EvaluationMetrics:
    ideal_encoded_fidelity: float | None = None
    noisy_encoded_fidelity: float | None = None
    logical_magic_witness: float | None = None
    acceptance_rate: float = 1.0
    codespace_rate: float | None = None
    spectator_logical_z: float | None = None
    logical_x: float | None = None
    logical_y: float | None = None
    stability_score: float | None = None
    two_qubit_count: int = 0
    depth: int = 0
    shot_count: int = 0
    runtime_estimate: float = 0.0
    queue_cost_proxy: float = 0.0
    total_cost: float = 0.0
    dominant_failure_mode: str = "unclassified"
    transpile_metadata: dict[str, Any] = field(default_factory=dict)
    backend_metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TierResult:
    tier: str
    score: float
    quality_estimate: float
    metrics: EvaluationMetrics
    counts_summary: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_timestamp)


@dataclass
class ExperimentRecord:
    experiment_id: str
    rung: int
    role: str
    parent_incumbent_id: str | None
    mutation_note: str
    spec: ExperimentSpec
    cheap_result: TierResult
    expensive_result: TierResult | None = None
    final_score: float = 0.0
    promoted_to_expensive: bool = False
    became_incumbent: bool = False
    created_at: str = field(default_factory=utc_timestamp)

    @property
    def best_result(self) -> TierResult:
        return self.expensive_result or self.cheap_result


@dataclass
class RatchetStepRecord:
    step_index: int
    rung: int
    incumbent_before_id: str
    challengers_tested: list[str]
    promoted_challengers: list[str]
    winner_id: str
    winning_margin: float
    cheap_tier_justification: str
    expensive_tier_result: str
    distilled_lesson: str
    created_at: str = field(default_factory=utc_timestamp)


@dataclass
class RungLesson:
    rung: int
    name: str
    objective: str
    what_helped: list[str]
    what_hurt: list[str]
    what_seems_invariant: list[str]
    what_seems_hardware_specific: list[str]
    what_should_be_tested_next: list[str]
    what_should_be_promoted_to_next_rung: list[str]
    what_should_be_discarded: list[str]
    narrative: str
    created_at: str = field(default_factory=utc_timestamp)


@dataclass(frozen=True)
class SearchRule:
    """Machine-readable directive extracted from lesson analysis."""
    dimension: str
    action: str  # "prefer", "avoid", "fix"
    value: Any
    confidence: float  # 0.0–1.0, based on sample proportion
    reason: str


@dataclass(frozen=True)
class LessonFeedback:
    """Machine-readable counterpart to RungLesson for search guidance."""
    rung: int
    rules: list[SearchRule]
    narrowed_dimensions: dict[str, list[Any]]
    best_spec_fields: dict[str, Any]
    transfer_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class TransferReport:
    """Cross-backend evaluation results for a single spec."""
    spec: ExperimentSpec
    per_backend_scores: dict[str, float]
    per_backend_metrics: dict[str, EvaluationMetrics]
    mean_score: float
    min_score: float
    max_score: float
    std_score: float
    transfer_score: float  # pessimistic = min(scores)


@dataclass
class FactoryMetrics:
    """Factory-style throughput metrics attached to EvaluationMetrics.extra."""
    accepted_states_per_shot: float
    logical_error_per_accepted: float
    accepted_per_unit_cost: float
    quality_yield: float
    cost_per_accepted: float
    throughput_proxy: float


@dataclass
class RungProgress:
    """Resumability state for a rung execution."""
    rung: int
    steps_completed: int
    patience_remaining: int
    current_incumbent_id: str
    completed: bool = False


def generate_experiment_id(spec: ExperimentSpec, role: str) -> str:
    return f"r{spec.rung}-{role}-{spec.fingerprint()}"
