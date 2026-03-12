"""Feed ranking rules isolated for future replacement."""

from __future__ import annotations

from dataclasses import dataclass

from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post


@dataclass(slots=True)
class FeedWeights:
    heat: float = 1.0
    freshness: float = 1.0
    topic_match: float = 1.0
    stance_affinity: float = 0.5
    official_boost: float = 1.2
    source_trust: float = 0.2
    social_proximity: float = 0.1
    novelty: float = 0.3


class FeedRanker:
    """Generate ranked feed items with transparent scoring reasons."""

    def __init__(self, weights: FeedWeights, max_items: int = 10) -> None:
        self.weights = weights
        self.max_items = max_items

    def _score_breakdown(self, agent: Agent, post: Post, step: int) -> dict[str, float]:
        heat_score = post.heat * self.weights.heat
        freshness_score = (1.0 / (1 + max(0, step - post.created_at_step))) * self.weights.freshness
        topic_match_score = (1.0 if post.topic in agent.interest_topics else 0.0) * self.weights.topic_match
        stance_affinity_raw = 1.0 if agent.topic_stances.get(post.topic, "neutral") == post.stance else 0.2
        stance_affinity_score = stance_affinity_raw * self.weights.stance_affinity
        official_boost_score = (1.0 if post.source_type in {"official", "fact_check"} else 0.0) * self.weights.official_boost
        source_trust_score = agent.trust_scores.get(post.source_type, 0.5) * self.weights.source_trust
        social_proximity_score = post.metadata.get("social_proximity", 0.0) * self.weights.social_proximity
        novelty_score = (0.0 if post.post_id in agent.seen_content_ids else 1.0) * self.weights.novelty

        return {
            "heat_score": round(heat_score, 4),
            "freshness_score": round(freshness_score, 4),
            "topic_match_score": round(topic_match_score, 4),
            "stance_affinity_score": round(stance_affinity_score, 4),
            "official_boost_score": round(official_boost_score, 4),
            "source_trust_score": round(source_trust_score, 4),
            "social_proximity_score": round(social_proximity_score, 4),
            "novelty_score": round(novelty_score, 4),
        }

    def rank(self, agent: Agent, posts: dict[str, Post], step: int) -> list[FeedItem]:
        items: list[FeedItem] = []
        for post in posts.values():
            if post.visibility != "public":
                continue
            breakdown = self._score_breakdown(agent, post, step)
            score = sum(breakdown.values())
            if post.post_id in agent.seen_content_ids:
                score *= 0.4
            reason = (
                f"heat={breakdown['heat_score']:.2f};fresh={breakdown['freshness_score']:.2f};"
                f"topic={breakdown['topic_match_score']:.2f};official={breakdown['official_boost_score']:.2f}"
            )
            items.append(
                FeedItem(
                    item_id=f"fi_{agent.agent_id}_{post.post_id}",
                    item_type="post",
                    ref_id=post.post_id,
                    score=round(score, 4),
                    reason=reason,
                    breakdown=breakdown,
                )
            )
        return sorted(items, key=lambda it: it.score, reverse=True)[: self.max_items]
