"""Simulation recorders for snapshots and structured logs."""

from __future__ import annotations

from dataclasses import asdict

from vasociety.models.state import SimulationState


class SnapshotRecorder:
    def record_step_snapshot(self, state: SimulationState) -> None:
        top_posts = sorted(state.posts.values(), key=lambda post: post.heat, reverse=True)[:3]
        state.snapshots.append(
            {
                "step": state.current_step,
                "post_count": len(state.posts),
                "comment_count": len(state.comments),
                "top_posts": [asdict(post) for post in top_posts],
            }
        )


class StructuredEventLogger:
    def log_perception(self, state: SimulationState, agent_id: str, visible_item_ids: list[str], ranked_reasons: list[dict]) -> None:
        state.event_log.append(
            {
                "step": state.current_step,
                "event": "perception_log",
                "agent_id": agent_id,
                "visible_item_ids": visible_item_ids,
                "ranked_reasons": ranked_reasons,
            }
        )

    def log_decision(self, state: SimulationState, agent_id: str, selected_action: str, target_id: str | None, reason: str, state_delta: dict) -> None:
        state.event_log.append(
            {
                "step": state.current_step,
                "event": "decision_log",
                "agent_id": agent_id,
                "selected_action": selected_action,
                "target_id": target_id,
                "decision_reason": reason,
                "state_delta": state_delta,
            }
        )
