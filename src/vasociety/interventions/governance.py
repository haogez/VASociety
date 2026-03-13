"""Platform governance controls applied by intervention handlers."""

from __future__ import annotations

from typing import Any

from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState


GOVERNANCE_TYPES = {"platform_boost", "platform_suppress", "official_pin", "targeted_push"}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


class GovernanceController:
    """Apply platform-level governance interventions in a structured way."""

    def apply(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        if intervention.type == "platform_boost":
            return self._platform_boost(intervention, state)
        if intervention.type == "platform_suppress":
            return self._platform_suppress(intervention, state)
        if intervention.type == "official_pin":
            return self._official_pin(intervention, state)
        if intervention.type == "targeted_push":
            return self._targeted_push(intervention, state)
        return {"status": "unsupported", "type": intervention.type}

    def _platform_boost(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        payload = dict(intervention.payload)
        target_post_ids = self._resolve_target_post_ids(payload, state)
        if not target_post_ids:
            return {
                "status": "noop",
                "type": intervention.type,
                "intervention_id": intervention.intervention_id,
                "reason": "no_target_posts",
            }

        boost_add = float(payload.get("boost_add", payload.get("boost_heat", 0.8)))
        boost_factor = float(payload.get("boost_factor", 1.0))
        pin_when_boosted = bool(payload.get("pin_when_boosted", False))
        for post_id in target_post_ids:
            post = state.posts[post_id]
            post.heat = round(max(0.03, post.heat * boost_factor + boost_add), 4)
            post.last_active_step = state.current_step
            post.metadata["platform_boost"] = {
                "intervention_id": intervention.intervention_id,
                "boost_add": boost_add,
                "boost_factor": boost_factor,
            }
            if pin_when_boosted and post_id not in state.official_pinned_content:
                state.official_pinned_content.append(post_id)
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "affected_post_ids": target_post_ids,
            "boost_add": boost_add,
            "boost_factor": boost_factor,
            "pin_when_boosted": pin_when_boosted,
        }

    def _platform_suppress(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        payload = dict(intervention.payload)
        target_post_ids = self._resolve_target_post_ids(payload, state)
        if not target_post_ids:
            return {
                "status": "noop",
                "type": intervention.type,
                "intervention_id": intervention.intervention_id,
                "reason": "no_target_posts",
            }

        suppress_factor = float(payload.get("suppress_factor", 0.35))
        suppressed = set(state.suppressed_content)
        for post_id in target_post_ids:
            suppressed.add(post_id)
            post = state.posts[post_id]
            post.heat = round(max(0.03, post.heat * suppress_factor), 4)
            post.metadata["suppressed"] = True
            post.metadata["suppressed_by"] = intervention.intervention_id
            post.last_active_step = state.current_step
        state.suppressed_content[:] = sorted(suppressed)
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "affected_post_ids": target_post_ids,
            "suppress_factor": suppress_factor,
        }

    def _official_pin(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        payload = dict(intervention.payload)
        target_post_ids = self._resolve_target_post_ids(payload, state)
        if not target_post_ids:
            return {
                "status": "noop",
                "type": intervention.type,
                "intervention_id": intervention.intervention_id,
                "reason": "no_target_posts",
            }

        visibility_scope = str(payload.get("visibility_scope", "official_global"))
        for post_id in target_post_ids:
            if post_id not in state.official_pinned_content:
                state.official_pinned_content.append(post_id)
            post = state.posts[post_id]
            post.visibility_scope = visibility_scope
            post.visibility = visibility_scope
            post.metadata["pinned"] = True
            post.metadata["pinned_by"] = intervention.intervention_id
            post.last_active_step = state.current_step
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "affected_post_ids": target_post_ids,
            "visibility_scope": visibility_scope,
        }

    def _targeted_push(self, intervention: Intervention, state: SimulationState) -> dict[str, Any]:
        payload = dict(intervention.payload)
        target_post_ids = self._resolve_target_post_ids(payload, state)
        target_agent_ids = self._resolve_target_agent_ids(payload, state)
        push_score = float(payload.get("push_score", 1.0))

        if not target_post_ids:
            return {
                "status": "reserved",
                "type": intervention.type,
                "intervention_id": intervention.intervention_id,
                "target_agent_ids": target_agent_ids,
                "reason": "no_target_posts",
            }

        for post_id in target_post_ids:
            post = state.posts[post_id]
            post.metadata["targeted_agent_ids"] = list(target_agent_ids)
            post.metadata["targeted_push"] = {
                "intervention_id": intervention.intervention_id,
                "push_score": push_score,
            }
            # Small heat bump keeps the hook visible for ranking experiments.
            post.heat = round(post.heat + min(0.5, 0.08 * push_score), 4)
            post.last_active_step = state.current_step
        return {
            "status": "applied",
            "type": intervention.type,
            "intervention_id": intervention.intervention_id,
            "affected_post_ids": target_post_ids,
            "target_agent_ids": target_agent_ids,
            "push_score": push_score,
        }

    @staticmethod
    def _resolve_target_post_ids(payload: dict[str, Any], state: SimulationState) -> list[str]:
        if "post_ids" in payload and isinstance(payload["post_ids"], list):
            candidates = [str(item) for item in payload["post_ids"]]
        elif "post_id" in payload:
            candidates = [str(payload["post_id"])]
        elif "topic" in payload:
            topic = str(payload["topic"])
            candidates = [post_id for post_id, post in state.posts.items() if post.topic == topic]
        else:
            candidates = []
        return _unique([post_id for post_id in candidates if post_id in state.posts])

    @staticmethod
    def _resolve_target_agent_ids(payload: dict[str, Any], state: SimulationState) -> list[str]:
        if "target_agent_ids" in payload and isinstance(payload["target_agent_ids"], list):
            candidates = [str(item) for item in payload["target_agent_ids"]]
            return _unique([agent_id for agent_id in candidates if agent_id in state.agents])
        if "target_persona_types" in payload and isinstance(payload["target_persona_types"], list):
            persona_types = {str(item) for item in payload["target_persona_types"]}
            return _unique([agent.agent_id for agent in state.agents.values() if agent.persona_type in persona_types])
        return []
