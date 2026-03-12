"""Action execution module to mutate simulation state from decisions."""

from __future__ import annotations

from dataclasses import asdict

from vasociety.agents.policy import Decision
from vasociety.models.agent import ActionRecord, Agent
from vasociety.models.content import Comment, Post
from vasociety.models.state import SimulationState


class ActionExecutor:
    """Execute agent actions and return execution summary."""

    def execute(self, state: SimulationState, agent: Agent, decision: Decision) -> dict[str, str | int | None]:
        action = decision.action
        target_id = decision.target_post_id
        content = decision.content
        stance = decision.stance or "neutral"

        if target_id and target_id in state.posts:
            agent.seen_content_ids.add(target_id)

        created_post_id: str | None = None
        created_comment_id: str | None = None

        if action == "like" and target_id and target_id in state.posts:
            state.posts[target_id].likes += 1
            state.posts[target_id].heat += 0.25
        elif action == "comment" and target_id and content and target_id in state.posts:
            created_comment_id = f"comment_{len(state.comments)+1:05d}"
            state.comments[created_comment_id] = Comment(
                comment_id=created_comment_id,
                post_id=target_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=content,
                stance=stance,
            )
            state.posts[target_id].comments_count += 1
            state.posts[target_id].heat += 0.35
        elif action == "repost" and target_id and target_id in state.posts:
            parent = state.posts[target_id]
            parent.reposts += 1
            parent.heat += 0.4
            created_post_id = f"post_{len(state.posts)+1:05d}"
            state.posts[created_post_id] = Post(
                post_id=created_post_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=f"转发：{parent.content}",
                topic=parent.topic,
                stance=parent.stance,
                source_type="organic",
                parent_post_id=target_id,
                heat=1.1,
            )
            agent.created_post_ids.append(created_post_id)
        elif action == "create_post" and content:
            topic = agent.current_focus_topics[0] if agent.current_focus_topics else agent.interest_topics[0]
            created_post_id = f"post_{len(state.posts)+1:05d}"
            state.posts[created_post_id] = Post(
                post_id=created_post_id,
                author_id=agent.agent_id,
                created_at_step=state.current_step,
                content=content,
                topic=topic,
                stance=stance,
                source_type="organic",
                heat=1.0,
            )
            agent.created_post_ids.append(created_post_id)

        agent.record_action(ActionRecord(step=state.current_step, action=action, target_id=target_id, content=content))

        execution = {
            "action": action,
            "target_id": target_id,
            "created_post_id": created_post_id,
            "created_comment_id": created_comment_id,
        }
        state.event_log.append(
            {
                "step": state.current_step,
                "event": "execution_log",
                "agent_id": agent.agent_id,
                "payload": execution,
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
                "decision_reason": decision.reason,
                "state_delta": decision.state_delta,
                "execution": execution,
            }
        )
        if decision.state_delta.get("stance_shifted"):
            state.stance_shift_count += 1

        return execution

    @staticmethod
    def serialize_agent(agent: Agent) -> dict:
        data = asdict(agent)
        data["seen_content_ids"] = sorted(agent.seen_content_ids)
        return data
