"""Agent model definitions and action records."""

from __future__ import annotations

from dataclasses import dataclass, field

from vasociety.types import ActionType


@dataclass(slots=True)
class ActionRecord:
    """Single action emitted by one agent at one simulation step."""

    step: int
    action: ActionType
    target_id: str | None = None
    content: str | None = None


@dataclass(slots=True)
class Agent:
    """Simplified but extensible phase-1 social agent."""

    agent_id: str
    name: str
    persona_type: str
    interest_topics: list[str]
    activity_profile: float
    expression_level: float
    conformity_level: float
    skepticism_level: float
    emotionality_level: float
    authority_trust_level: float
    is_registered: bool = True
    is_online: bool = False
    current_emotion: str = "neutral"
    current_focus_topics: list[str] = field(default_factory=list)
    seen_content_ids: set[str] = field(default_factory=set)
    created_post_ids: list[str] = field(default_factory=list)
    action_history: list[ActionRecord] = field(default_factory=list)
    topic_beliefs: dict[str, float] = field(default_factory=dict)
    topic_uncertainty: dict[str, float] = field(default_factory=dict)
    topic_stances: dict[str, str] = field(default_factory=dict)
    trust_scores: dict[str, float] = field(default_factory=dict)
    stance_update_history: list[dict[str, str | int | float]] = field(default_factory=list)

    def record_action(self, record: ActionRecord) -> None:
        self.action_history.append(record)
