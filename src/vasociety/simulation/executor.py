"""Action execution module to mutate simulation state from decisions."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from vasociety.agents.policy import Decision
from vasociety.models.agent import ActionRecord, Agent
from vasociety.models.content import Comment, Post
from vasociety.models.state import SimulationState
from vasociety.social.trust import update_trust_by_interaction

if TYPE_CHECKING:
    from vasociety.simulation.recorder import StructuredEventLogger


SUPPORTED_ACTIONS = {
    "skip",
    "like",
    "comment",
    "repost",
    "create_post",
    "bookmark",
    "follow",
}
POST_TARGET_ACTIONS = {"like", "comment", "repost", "bookmark"}
TRUST_IMPACT_ACTIONS = {"like", "comment", "repost"}


class ActionExecutor:
    """Centralized action executor with validation, execution, and effects emission."""

    def validate_action(self, state: SimulationState, agent: Agent, decision: Decision) -> tuple[bool, str | None]:
        action = str(decision.action)
        target_id = decision.target_post_id

        if action not in SUPPORTED_ACTIONS:
            return False, f"unsupported_action:{action}"
        if action in POST_TARGET_ACTIONS:
            if not target_id:
                return False, f"missing_target_for_{action}"
            if target_id not in state.posts:
                return False, f"post_not_found:{target_id}"
        if action == "follow":
            if not target_id:
                return False, "missing_target_for_follow"
            if target_id == agent.agent_id:
                return False, "cannot_follow_self"
            if target_id not in state.agents:
                return False, f"agent_not_found:{target_id}"
        return True, None

    def execute_action(self, state: SimulationState, agent: Agent, decision: Decision) -> dict[str, Any]:
        action = str(decision.action)
        target_id = decision.target_post_id
        stance = decision.stance or "neutral"
        valid, error = self.validate_action(state, agent, decision)
        execution: dict[str, Any] = {
            "status": "executed",
            "action": action,
            "target_id": target_id,
            "created_post_id": None,
            "created_comment_id": None,
        }
        if not valid:
            execution["status"] = "rejected"
            execution["rejection_reason"] = error
            return execution

        if target_id and target_id in state.posts:
            self._mark_post_exposure(state, agent, target_id)

        if action == "skip":
            execution["status"] = "noop"
            execution["effect"] = "skip"
            return execution

        if action == "like" and target_id and target_id in state.posts:
            state.posts[target_id].likes += 1
            state.posts[target_id].heat += 0.25
            state.posts[target_id].last_active_step = state.current_step
            execution["effect"] = "liked_post"
            return execution

        if action == "comment" and target_id and target_id in state.posts:
            post = state.posts[target_id]
            comment_text = self._resolve_comment_content(agent, post, decision.content)
            comment_id = state.next_comment_id()
            state.comments[comment_id] = Comment(
                comment_id=comment_id,
                post_id=target_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=comment_text,
                stance=stance,
            )
            post.comments_count += 1
            post.heat += 0.35
            post.last_active_step = state.current_step
            execution["created_comment_id"] = comment_id
            execution["content"] = comment_text
            execution["effect"] = "comment_created"
            return execution

        if action == "repost" and target_id and target_id in state.posts:
            parent = state.posts[target_id]
            parent.reposts += 1
            parent.heat += 0.4
            parent.last_active_step = state.current_step

            post_id = state.next_post_id()
            diffusion_path = self._build_diffusion_path(parent, post_id)
            origin_post_id = parent.origin_post_id or parent.post_id
            state.posts[post_id] = Post(
                post_id=post_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=f"转发：{parent.content}",
                topic=parent.topic,
                stance=parent.stance,
                source_type="organic",
                parent_post_id=target_id,
                origin_post_id=origin_post_id,
                diffusion_path=diffusion_path,
                heat=1.1,
                last_active_step=state.current_step,
            )
            agent.created_post_ids.append(post_id)
            execution["created_post_id"] = post_id
            execution["parent_post_id"] = target_id
            execution["origin_post_id"] = origin_post_id
            execution["diffusion_path"] = diffusion_path
            execution["effect"] = "repost_created"
            return execution

        if action == "create_post":
            topic = agent.current_focus_topics[0] if agent.current_focus_topics else agent.interest_topics[0]
            post_id = state.next_post_id()
            post_content = self._resolve_post_content(agent, topic, stance, decision.content)
            state.posts[post_id] = Post(
                post_id=post_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=post_content,
                topic=topic,
                stance=stance,
                source_type="organic",
                origin_post_id=post_id,
                diffusion_path=[post_id],
                heat=1.0,
                last_active_step=state.current_step,
            )
            agent.created_post_ids.append(post_id)
            execution["created_post_id"] = post_id
            execution["origin_post_id"] = post_id
            execution["diffusion_path"] = [post_id]
            execution["content"] = post_content
            execution["effect"] = "post_created"
            return execution

        if action == "bookmark" and target_id and target_id in state.posts:
            post = state.posts[target_id]
            bookmark_count = int(post.metadata.get("bookmark_count", 0))
            post.metadata["bookmark_count"] = bookmark_count + 1
            post.last_active_step = state.current_step
            execution["effect"] = "bookmark_reserved"
            return execution

        if action == "follow" and target_id:
            self._apply_follow_edge(state, agent_id=agent.agent_id, target_agent_id=target_id)
            execution["target_agent_id"] = target_id
            execution["effect"] = "follow_reserved"
            return execution

        execution["status"] = "rejected"
        execution["rejection_reason"] = f"unhandled_action:{action}"
        return execution

    def emit_action_effects(
        self,
        state: SimulationState,
        agent: Agent,
        decision: Decision,
        execution: dict[str, Any],
        structured_logger: StructuredEventLogger | None = None,
    ) -> dict[str, Any]:
        action = str(execution.get("action", decision.action))
        target_id = execution.get("target_id", decision.target_post_id)
        status = str(execution.get("status", "executed"))

        if status != "rejected":
            record_content = execution.get("content", decision.content)
            agent.record_action(
                ActionRecord(
                    step=state.current_step,
                    action=action,
                    target_id=target_id,
                    content=record_content,
                )
            )

        if status == "executed" and action in TRUST_IMPACT_ACTIONS and target_id and target_id in state.posts:
            target_post = state.posts[target_id]
            trust_update = update_trust_by_interaction(
                state=state,
                actor_id=agent.agent_id,
                target_author_id=target_post.author_id,
                action=action,
                stance_conflict=self._stance_conflict(agent, target_post),
                interaction_count=self._interaction_count_with_author(state, agent, target_post.author_id),
            )
            execution["trust_update"] = trust_update

        if structured_logger is not None:
            structured_logger.log_execution(
                state=state,
                agent_id=agent.agent_id,
                decision=decision,
                execution=execution,
            )
        else:
            state.event_log.append(
                {
                    "step": state.current_step,
                    "event": "execution_log",
                    "agent_id": agent.agent_id,
                    "payload": dict(execution),
                }
            )
            state.decision_trace.append(
                {
                    "step": state.current_step,
                    "agent_id": agent.agent_id,
                    "visible_item_ids": decision.visible_item_ids,
                    "ranked_reasons": decision.ranked_reasons,
                    "selected_action": decision.action,
                    "target_id": decision.target_post_id,
                    "decision_reason": decision.decision_reason or decision.reason,
                    "state_delta": decision.state_delta,
                    "execution": dict(execution),
                }
            )
        if decision.state_delta.get("stance_shifted"):
            state.stance_shift_count += 1

        return execution

    def execute(
        self,
        state: SimulationState,
        agent: Agent,
        decision: Decision,
        structured_logger: StructuredEventLogger | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible wrapper used by engine."""

        execution = self.execute_action(state=state, agent=agent, decision=decision)
        return self.emit_action_effects(
            state=state,
            agent=agent,
            decision=decision,
            execution=execution,
            structured_logger=structured_logger,
        )

    @staticmethod
    def serialize_agent(agent: Agent) -> dict:
        data = asdict(agent)
        data["seen_content_ids"] = sorted(agent.seen_content_ids)
        return data

    @staticmethod
    def _resolve_comment_content(agent: Agent, post: Post, content: str | None) -> str:
        text = (content or "").strip()
        if text:
            return text
        stance = agent.topic_stances.get(post.topic, "neutral")
        return f"我在看{post.topic}，当前倾向{stance}，先补充一条观察。"

    @staticmethod
    def _resolve_post_content(agent: Agent, topic: str, stance: str, content: str | None) -> str:
        text = (content or "").strip()
        if text:
            return text
        return f"关于{topic}，我目前更偏向{stance}，仍在持续观察。"

    @staticmethod
    def _build_diffusion_path(parent: Post, created_post_id: str) -> list[str]:
        if parent.diffusion_path:
            path = list(parent.diffusion_path)
        else:
            path = [parent.origin_post_id or parent.post_id]
        if not path or path[-1] != parent.post_id:
            path.append(parent.post_id)
        path.append(created_post_id)
        return path

    @staticmethod
    def _mark_post_exposure(state: SimulationState, agent: Agent, post_id: str) -> None:
        post = state.posts[post_id]
        if post_id not in agent.seen_content_ids:
            post.exposure_count += 1
        agent.seen_content_ids.add(post_id)

    @staticmethod
    def _interaction_count_with_author(state: SimulationState, agent: Agent, author_id: str) -> int:
        return sum(
            1
            for record in agent.action_history
            if record.action in TRUST_IMPACT_ACTIONS
            and record.target_id in state.posts
            and state.posts[record.target_id].author_id == author_id
        )

    @staticmethod
    def _apply_follow_edge(state: SimulationState, agent_id: str, target_agent_id: str) -> None:
        followees = state.followees.setdefault(agent_id, [])
        if target_agent_id not in followees:
            followees.append(target_agent_id)
        followers = state.followers.setdefault(target_agent_id, [])
        if agent_id not in followers:
            followers.append(agent_id)
        state.trust_edges.setdefault(agent_id, {}).setdefault(target_agent_id, 0.55)

    @staticmethod
    def _stance_conflict(agent: Agent, target_post: Post) -> float:
        topic_stance = agent.topic_stances.get(target_post.topic, "neutral")
        if topic_stance == target_post.stance:
            return 0.0
        if topic_stance == "neutral" or target_post.stance == "neutral":
            return 0.35
        return 0.75
