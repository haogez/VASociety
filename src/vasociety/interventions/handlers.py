"""Intervention handlers for injecting platform content."""

from __future__ import annotations

from typing import Any

from vasociety.interventions.governance import GOVERNANCE_TYPES, GovernanceController
from vasociety.models.content import Post
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState


class InterventionHandler:
    """Apply supported intervention types to simulation state."""

    def __init__(self, governance: GovernanceController | None = None) -> None:
        self.governance = governance or GovernanceController()

    def apply(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        if intervention.type == "inject_news":
            return self._inject_news(intervention, state)
        if intervention.type == "inject_fact_check":
            return self._inject_fact_check(intervention, state)
        if intervention.type in GOVERNANCE_TYPES:
            return self.governance.apply(intervention, state)
        return {
            "status": "unsupported",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
        }

    @staticmethod
    def _inject_news(intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        post_id = state.next_post_id()
        payload = dict(intervention.payload)
        visibility_scope = payload.get("visibility_scope", payload.get("visibility", "public"))
        state.posts[post_id] = Post(
            post_id=post_id,
            author_id="system_news",
            created_at_step=state.current_step,
            content=str(payload["content"]),
            topic=str(payload["topic"]),
            stance=payload.get("stance", "uncertain"),
            source_type=payload.get("source_type", "official"),
            origin_post_id=post_id,
            diffusion_path=[post_id],
            visibility_scope=visibility_scope,
            visibility=visibility_scope,
            heat=2.0,
            last_active_step=state.current_step,
            metadata={"intervention_id": intervention.intervention_id, "kind": "news"},
        )
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "created_post_ids": [post_id],
            "visibility_scope": visibility_scope,
        }

    @staticmethod
    def _inject_fact_check(intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        post_id = state.next_post_id()
        payload = dict(intervention.payload)
        visibility_scope = payload.get("visibility_scope", payload.get("visibility", "public"))
        state.posts[post_id] = Post(
            post_id=post_id,
            author_id="system_fact_check",
            created_at_step=state.current_step,
            content=str(payload["content"]),
            topic=str(payload["topic"]),
            stance=payload.get("stance", "corrective"),
            source_type="fact_check",
            origin_post_id=post_id,
            diffusion_path=[post_id],
            visibility_scope=visibility_scope,
            visibility=visibility_scope,
            heat=2.2,
            last_active_step=state.current_step,
            metadata={"intervention_id": intervention.intervention_id, "kind": "fact_check"},
        )
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "created_post_ids": [post_id],
            "visibility_scope": visibility_scope,
        }
