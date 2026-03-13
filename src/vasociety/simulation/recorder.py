"""Simulation recorders for snapshots and structured logs."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from vasociety.models.state import SimulationState

if TYPE_CHECKING:
    from vasociety.agents.policy import Decision
    from vasociety.models.intervention import Intervention
    from vasociety.models.metrics import MetricsSnapshot


class SnapshotRecorder:
    def record_step_snapshot(self, state: SimulationState) -> None:
        top_posts = sorted(state.posts.values(), key=lambda post: post.heat, reverse=True)[:3]
        state.snapshots.append(
            {
                "step": state.current_step,
                "post_count": len(state.posts),
                "comment_count": len(state.comments),
                "top_posts": [asdict(post) for post in top_posts],
                "platform_state": {
                    "trending_pool": list(state.trending_pool),
                    "official_pinned_content": list(state.official_pinned_content),
                    "suppressed_content": list(state.suppressed_content),
                },
                "exposure_summary": {post.post_id: post.exposure_count for post in top_posts},
            }
        )


class StructuredEventLogger:
    @staticmethod
    def append_event(
        state: SimulationState,
        event: str,
        payload: dict[str, Any] | None = None,
        **extra_fields: Any,
    ) -> None:
        record: dict[str, Any] = {
            "schema_version": "event_log.v2",
            "step": state.current_step,
            "event": event,
        }
        if payload is not None:
            record["payload"] = payload
        for key, value in extra_fields.items():
            if value is not None:
                record[key] = value
        state.event_log.append(record)

    def log_intervention(self, state: SimulationState, intervention: Intervention, result: dict[str, Any]) -> None:
        self.append_event(
            state,
            event="intervention",
            payload={
                "intervention_id": intervention.intervention_id,
                "type": intervention.type,
                "payload": intervention.payload,
                "result": result,
            },
        )

    def log_metrics(self, state: SimulationState, metrics: MetricsSnapshot) -> None:
        self.append_event(state, event="metrics", payload=asdict(metrics))

    def log_perception(self, state: SimulationState, agent_id: str, visible_item_ids: list[str], ranked_reasons: list[dict]) -> None:
        visible_items = []
        for reason in ranked_reasons:
            if not isinstance(reason, dict):
                continue
            breakdown = dict(reason.get("breakdown", {}))
            visibility_hints = self._extract_visibility_hints(reason)
            visible_items.append(
                {
                    "ref_id": reason.get("ref_id"),
                    "score": reason.get("score"),
                    "rank_reason": reason.get("reason"),
                    "score_breakdown": breakdown,
                    "visibility_hints": visibility_hints,
                    "evaluation": reason.get("evaluation"),
                }
            )
        self.append_event(
            state,
            event="perception_log",
            payload={
                "agent_id": agent_id,
                "visible_item_ids": list(visible_item_ids),
                "visible_items": visible_items,
                "visible_count": len(visible_item_ids),
            },
            agent_id=agent_id,
            visible_item_ids=visible_item_ids,
            ranked_reasons=ranked_reasons,
        )

    def log_decision(
        self,
        state: SimulationState,
        agent_id: str,
        selected_action: str,
        target_id: str | None,
        reason: str,
        state_delta: dict,
        visible_item_ids: list[str] | None = None,
        ranked_reasons: list[dict] | None = None,
    ) -> None:
        self.append_event(
            state,
            event="decision_log",
            payload={
                "agent_id": agent_id,
                "selected_action": selected_action,
                "target_id": target_id,
                "decision_reason": reason,
                "state_delta": dict(state_delta),
                "visible_item_ids": list(visible_item_ids or []),
                "ranked_reasons": list(ranked_reasons or []),
            },
            agent_id=agent_id,
            selected_action=selected_action,
            target_id=target_id,
            decision_reason=reason,
            state_delta=state_delta,
        )

    def log_execution(self, state: SimulationState, agent_id: str, decision: Decision, execution: dict[str, Any]) -> None:
        self.append_event(
            state,
            event="execution_log",
            payload={
                "agent_id": agent_id,
                "selected_action": decision.action,
                "target_id": decision.target_post_id,
                "decision_reason": decision.decision_reason or decision.reason,
                "state_delta": dict(decision.state_delta),
                "execution": dict(execution),
            },
            agent_id=agent_id,
            selected_action=decision.action,
            target_id=decision.target_post_id,
            decision_reason=decision.decision_reason or decision.reason,
        )
        state.decision_trace.append(
            {
                "schema_version": "decision_trace.v2",
                "trace_type": "decision_execution",
                "step": state.current_step,
                "agent_id": agent_id,
                "visible_item_ids": decision.visible_item_ids,
                "ranked_reasons": decision.ranked_reasons,
                "selected_action": decision.action,
                "target_id": decision.target_post_id,
                "decision_reason": decision.decision_reason or decision.reason,
                "state_delta": decision.state_delta,
                "execution": dict(execution),
            }
        )

    @staticmethod
    def _extract_visibility_hints(reason: dict[str, Any]) -> list[str]:
        def _safe_float(value: Any) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        hints: list[str] = []
        breakdown = reason.get("breakdown")
        if isinstance(breakdown, dict):
            if _safe_float(breakdown.get("official_boost_score", 0.0)) > 0:
                hints.append("official_boost")
            if _safe_float(breakdown.get("social_proximity_score", 0.0)) > 0:
                hints.append("social_proximity")
            if _safe_float(breakdown.get("novelty_score", 0.0)) <= 0:
                hints.append("seen_content")
        text = str(reason.get("reason", ""))
        if "strategy=" in text:
            hints.append("ranked_by_strategy")
        return hints
