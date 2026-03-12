"""Simulation runtime state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vasociety.models.agent import Agent
from vasociety.models.content import Comment, Post
from vasociety.models.intervention import Intervention
from vasociety.models.metrics import MetricsSnapshot


@dataclass(slots=True)
class SimulationState:
    current_step: int = 0
    agents: dict[str, Agent] = field(default_factory=dict)
    posts: dict[str, Post] = field(default_factory=dict)
    comments: dict[str, Comment] = field(default_factory=dict)
    interventions: list[Intervention] = field(default_factory=list)
    metrics_history: list[MetricsSnapshot] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    decision_trace: list[dict[str, Any]] = field(default_factory=list)
    stance_shift_count: int = 0
