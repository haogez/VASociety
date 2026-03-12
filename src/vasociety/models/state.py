"""Simulation state and metric snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vasociety.models.agent import Agent
from vasociety.models.content import Comment, Post
from vasociety.models.intervention import Intervention


@dataclass(slots=True)
class MetricsSnapshot:
    """Step-level aggregated indicators."""

    step: int
    total_posts: int
    total_comments: int
    total_likes: int
    total_reposts: int
    stance_distribution: dict[str, float]
    discussion_heat: float
    active_agents: int


@dataclass(slots=True)
class SimulationState:
    """In-memory state object mutated by the simulation engine."""

    current_step: int = 0
    agents: dict[str, Agent] = field(default_factory=dict)
    posts: dict[str, Post] = field(default_factory=dict)
    comments: dict[str, Comment] = field(default_factory=dict)
    interventions: list[Intervention] = field(default_factory=list)
    metrics_history: list[MetricsSnapshot] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
