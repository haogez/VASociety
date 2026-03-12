"""Feed ranking rules isolated for future replacement."""

from __future__ import annotations

from dataclasses import dataclass

from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post


@dataclass(slots=True)
class FeedWeights:
    """Weights for additive ranking score."""

    heat: float = 1.0
    freshness: float = 1.0
    topic_match: float = 1.0
    stance_alignment: float = 0.5
    stance_conflict: float = 0.2
    official_boost: float = 1.2


class FeedRanker:
    """Generate ranked feed items with transparent scoring reasons."""

    def __init__(self, weights: FeedWeights, max_items: int = 10) -> None:
        self.weights = weights
        self.max_items = max_items

    def rank(self, agent: Agent, posts: dict[str, Post], step: int) -> list[FeedItem]:
        """Rank visible posts for one agent."""

        items: list[FeedItem] = []
        for post in posts.values():
            if post.visibility != "public":
                continue
            freshness = 1.0 / (1 + max(0, step - post.created_at_step))
            topic_match = 1.0 if post.topic in agent.interest_topics else 0.0
            alignment = 1.0 if post.stance in {"supportive", "corrective"} else 0.0
            conflict = 1.0 if post.stance in {"questioning", "opposed"} else 0.0
            official = 1.0 if post.source_type in {"official", "fact_check"} else 0.0
            score = (
                post.heat * self.weights.heat
                + freshness * self.weights.freshness
                + topic_match * self.weights.topic_match
                + alignment * self.weights.stance_alignment
                + conflict * self.weights.stance_conflict
                + official * self.weights.official_boost
            )
            if post.post_id in agent.seen_content_ids:
                score *= 0.3

            reason = f"heat={post.heat:.2f},fresh={freshness:.2f},topic={topic_match:.1f},official={official:.1f}"
            items.append(FeedItem(item_id=f"fi_{agent.agent_id}_{post.post_id}", item_type="post", ref_id=post.post_id, score=score, reason=reason))

        return sorted(items, key=lambda it: it.score, reverse=True)[: self.max_items]
