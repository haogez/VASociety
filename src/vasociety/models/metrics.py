"""Metric snapshot schema for experiment-oriented analysis."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MetricsSnapshot:
    step: int
    total_posts: int
    total_comments: int
    total_likes: int
    total_reposts: int
    discussion_heat: float
    active_agents: int
    stance_distribution: dict[str, float]
    persona_participation: dict[str, int] = field(default_factory=dict)
    per_persona_action_distribution: dict[str, dict[str, int]] = field(default_factory=dict)
    rumor_like_content_count: int = 0
    corrective_content_count: int = 0
    rumor_spread_coverage: float = 0.0
    corrective_spread_coverage: float = 0.0
    stance_shift_count: int = 0
    per_step_topic_heat: dict[str, float] = field(default_factory=dict)
    intervention_event_count: int = 0
    governance_action_count: int = 0
    suppressed_content_count: int = 0
    pinned_content_count: int = 0
    intervention_type_counts: dict[str, int] = field(default_factory=dict)
