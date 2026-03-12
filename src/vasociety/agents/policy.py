"""Rule-based policy for phase-1 agent decisions."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from vasociety.agents.belief import update_topic_belief
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post
from vasociety.types import ActionType


@dataclass(slots=True)
class Decision:
    action: ActionType
    target_post_id: str | None = None
    content: str | None = None
    stance: str | None = None
    reason: str = ""
    visible_item_ids: list[str] = field(default_factory=list)
    ranked_reasons: list[dict[str, str | float | dict[str, float]]] = field(default_factory=list)
    state_delta: dict[str, str | float | int | bool] = field(default_factory=dict)


class AgentPolicy:
    """Deterministic pseudo-random rule set based on persona attributes."""

    def __init__(self, seed: int, view_top_k: int = 3) -> None:
        self._rng = random.Random(seed)
        self.view_top_k = view_top_k

    def perceive(self, agent: Agent, feed: list[FeedItem]) -> tuple[list[FeedItem], list[str], list[dict[str, str | float | dict[str, float]]]]:
        visible = feed[: self.view_top_k]
        visible_ids = [item.ref_id for item in visible]
        ranked_reasons = [
            {"ref_id": item.ref_id, "score": item.score, "reason": item.reason, "breakdown": item.breakdown}
            for item in visible
        ]
        return visible, visible_ids, ranked_reasons

    def update_beliefs(self, agent: Agent, visible: list[FeedItem], posts: dict[str, Post], step: int) -> dict[str, str | float | int | bool]:
        delta: dict[str, str | float | int | bool] = {}
        for item in visible:
            post = posts[item.ref_id]
            result = update_topic_belief(agent, post, step)
            if result["stance_shifted"]:
                delta = result
        return delta

    def decide_action(self, agent: Agent, visible: list[FeedItem], posts: dict[str, Post]) -> Decision:
        if not visible:
            return self._maybe_create_post(agent, None, reason="empty_feed")

        unseen = [item for item in visible if item.ref_id not in agent.seen_content_ids]
        if not unseen:
            return Decision(action="skip", reason="all_seen")

        selected = unseen[0]
        post = posts[selected.ref_id]
        reaction_score = post.heat * 0.2 + agent.expression_level + agent.emotionality_level * 0.25
        if post.topic in agent.interest_topics:
            reaction_score += 0.35
        if post.source_type in {"official", "fact_check"}:
            reaction_score += agent.authority_trust_level * 0.3
        if post.stance == "corrective":
            reaction_score -= 0.1 * agent.emotionality_level

        roll = self._rng.random()
        if reaction_score > 1.25 and roll < 0.35 + agent.expression_level * 0.2:
            return Decision(action="repost", target_post_id=post.post_id, reason="high_reaction_repost")
        if reaction_score > 0.95 and roll < 0.75:
            return Decision(
                action="comment",
                target_post_id=post.post_id,
                content=self._make_comment(agent, post),
                stance=self._derive_stance(agent, post),
                reason="medium_reaction_comment",
            )
        if reaction_score > 0.6:
            return Decision(action="like", target_post_id=post.post_id, reason="low_reaction_like")
        if roll < max(0.05, agent.expression_level * 0.2):
            return self._maybe_create_post(agent, post.topic, reason="self_expression")
        return Decision(action="skip", target_post_id=post.post_id, reason="insufficient_reaction")

    def decide(self, agent: Agent, feed: list[FeedItem], posts: dict[str, Post], step: int) -> Decision:
        visible, visible_ids, ranked_reasons = self.perceive(agent, feed)
        delta = self.update_beliefs(agent, visible, posts, step)
        decision = self.decide_action(agent, visible, posts)
        decision.visible_item_ids = visible_ids
        decision.ranked_reasons = ranked_reasons
        decision.state_delta = delta
        return decision

    def _maybe_create_post(self, agent: Agent, topic: str | None, reason: str) -> Decision:
        if self._rng.random() < agent.expression_level * 0.25:
            chosen_topic = topic or self._rng.choice(agent.interest_topics)
            stance = agent.topic_stances.get(chosen_topic, "questioning")
            return Decision(
                action="create_post",
                content=f"关于{chosen_topic}，我目前更偏向{stance}，仍在持续观察。",
                stance=stance,
                reason=reason,
            )
        return Decision(action="skip", reason=reason)

    @staticmethod
    def _make_comment(agent: Agent, post: Post) -> str:
        if post.source_type == "fact_check":
            return "如果辟谣属实，那之前的信息可能有误。"
        if agent.emotionality_level > 0.7:
            return "这件事太离谱了，我觉得需要继续关注。"
        return "我倾向于相信这个消息，但还需要更多证据。"

    @staticmethod
    def _derive_stance(agent: Agent, post: Post) -> str:
        topic_stance = agent.topic_stances.get(post.topic, "neutral")
        if topic_stance != "neutral":
            return topic_stance
        return post.stance if agent.conformity_level > 0.5 else "questioning"
