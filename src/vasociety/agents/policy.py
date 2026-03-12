"""Rule-based policy for phase-1 agent decisions."""

from __future__ import annotations

import random
from dataclasses import dataclass

from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post
from vasociety.types import ActionType


@dataclass(slots=True)
class Decision:
    """Policy output representing one chosen action."""

    action: ActionType
    target_post_id: str | None = None
    content: str | None = None
    stance: str | None = None


class AgentPolicy:
    """Deterministic pseudo-random rule set based on persona attributes."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def decide(self, agent: Agent, feed: list[FeedItem], posts: dict[str, Post]) -> Decision:
        """Choose an action from feed and agent internal traits."""

        if not feed:
            return self._maybe_create_post(agent, None)

        selected = feed[0]
        post = posts[selected.ref_id]
        if post.post_id in agent.seen_content_ids:
            return Decision(action="skip", target_post_id=post.post_id)

        reaction_score = post.heat * 0.2 + agent.expression_level + agent.emotionality_level * 0.3
        if post.source_type in {"official", "fact_check"}:
            reaction_score += agent.authority_trust_level * 0.4
        if post.topic in agent.interest_topics:
            reaction_score += 0.4
        if post.stance == "corrective":
            reaction_score -= agent.emotionality_level * 0.2

        roll = self._rng.random()
        if reaction_score > 1.2 and roll < 0.35 + agent.expression_level * 0.2:
            return Decision(action="repost", target_post_id=post.post_id)
        if reaction_score > 0.9 and roll < 0.7:
            return Decision(
                action="comment",
                target_post_id=post.post_id,
                content=self._make_comment(agent, post),
                stance=self._derive_stance(agent, post),
            )
        if reaction_score > 0.6:
            return Decision(action="like", target_post_id=post.post_id)
        if roll < 0.15:
            return self._maybe_create_post(agent, post.topic)
        return Decision(action="skip", target_post_id=post.post_id)

    def _maybe_create_post(self, agent: Agent, topic: str | None) -> Decision:
        if self._rng.random() < agent.expression_level * 0.25:
            chosen_topic = topic or self._rng.choice(agent.interest_topics)
            stance = "supportive" if agent.authority_trust_level > 0.5 else "questioning"
            content = self._make_new_post(chosen_topic, stance)
            return Decision(action="create_post", content=content, stance=stance)
        return Decision(action="skip")

    @staticmethod
    def _make_comment(agent: Agent, post: Post) -> str:
        if post.source_type == "fact_check":
            return "如果辟谣属实，那之前的信息可能有误。"
        if agent.emotionality_level > 0.7:
            return "这件事太离谱了，我觉得需要继续关注。"
        return "我倾向于相信这个消息，但还需要更多证据。"

    @staticmethod
    def _make_new_post(topic: str, stance: str) -> str:
        return f"关于{topic}，我当前的看法是{stance}，欢迎补充更多信息。"

    @staticmethod
    def _derive_stance(agent: Agent, post: Post) -> str:
        if post.source_type == "fact_check" and agent.skepticism_level > 0.5:
            return "corrective"
        return post.stance if agent.conformity_level > 0.5 else "questioning"
