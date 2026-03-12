"""Intervention handlers for injecting platform content."""

from __future__ import annotations

from vasociety.models.content import Post
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState


class InterventionHandler:
    """Apply supported intervention types to simulation state."""

    def apply(self, intervention: Intervention, state: SimulationState) -> dict[str, str]:
        if intervention.type == "inject_news":
            self._inject_news(intervention, state)
        elif intervention.type == "inject_fact_check":
            self._inject_fact_check(intervention, state)
        elif intervention.type in {"platform_boost", "platform_suppress", "targeted_push"}:
            return {"status": "reserved", "type": intervention.type}
        return {"status": "applied", "type": intervention.type}

    @staticmethod
    def _inject_news(intervention: Intervention, state: SimulationState) -> None:
        post_id = f"post_{len(state.posts)+1:05d}"
        payload = intervention.payload
        state.posts[post_id] = Post(
            post_id=post_id,
            author_id="system_news",
            created_at_step=state.current_step,
            content=payload["content"],
            topic=payload["topic"],
            stance=payload.get("stance", "uncertain"),
            source_type=payload.get("source_type", "official"),
            visibility=payload.get("visibility", "public"),
            heat=2.0,
            metadata={"intervention_id": intervention.intervention_id, "kind": "news"},
        )

    @staticmethod
    def _inject_fact_check(intervention: Intervention, state: SimulationState) -> None:
        post_id = f"post_{len(state.posts)+1:05d}"
        payload = intervention.payload
        state.posts[post_id] = Post(
            post_id=post_id,
            author_id="system_fact_check",
            created_at_step=state.current_step,
            content=payload["content"],
            topic=payload["topic"],
            stance=payload.get("stance", "corrective"),
            source_type="fact_check",
            visibility=payload.get("visibility", "public"),
            heat=2.2,
            metadata={"intervention_id": intervention.intervention_id, "kind": "fact_check"},
        )
