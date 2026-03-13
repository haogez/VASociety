"""Componentized feed ranking rules with strategy switching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post

RankingStrategy = Literal["hotness_first", "interest_first", "social_first", "balanced"]

STRATEGY_MULTIPLIERS: dict[RankingStrategy, dict[str, float]] = {
    "balanced": {
        "heat_score": 1.0,
        "freshness_score": 1.0,
        "topic_match_score": 1.0,
        "stance_affinity_score": 1.0,
        "official_boost_score": 1.0,
        "source_trust_score": 1.0,
        "social_proximity_score": 1.0,
        "novelty_score": 1.0,
    },
    "hotness_first": {
        "heat_score": 1.8,
        "freshness_score": 1.4,
        "topic_match_score": 0.7,
        "stance_affinity_score": 0.8,
        "official_boost_score": 1.0,
        "source_trust_score": 0.8,
        "social_proximity_score": 0.9,
        "novelty_score": 0.4,
    },
    "interest_first": {
        "heat_score": 0.7,
        "freshness_score": 0.8,
        "topic_match_score": 2.3,
        "stance_affinity_score": 1.6,
        "official_boost_score": 0.8,
        "source_trust_score": 1.0,
        "social_proximity_score": 0.9,
        "novelty_score": 1.2,
    },
    "social_first": {
        "heat_score": 0.2,
        "freshness_score": 0.6,
        "topic_match_score": 0.3,
        "stance_affinity_score": 0.9,
        "official_boost_score": 0.8,
        "source_trust_score": 1.5,
        "social_proximity_score": 6.0,
        "novelty_score": 0.8,
    },
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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


def heat_score(post: Post, weights: FeedWeights) -> float:
    return post.heat * weights.heat


def freshness_score(post: Post, step: int, weights: FeedWeights) -> float:
    return (1.0 / (1 + max(0, step - post.created_at_step))) * weights.freshness


def topic_match_score(agent: Agent, post: Post, weights: FeedWeights) -> float:
    return (1.0 if post.topic in agent.interest_topics else 0.0) * weights.topic_match


def stance_affinity_score(agent: Agent, post: Post, weights: FeedWeights) -> float:
    affinity = 1.0 if agent.topic_stances.get(post.topic, "neutral") == post.stance else 0.2
    return affinity * weights.stance_affinity


def official_boost_score(post: Post, weights: FeedWeights) -> float:
    return (1.0 if post.source_type in {"official", "fact_check"} else 0.0) * weights.official_boost


def source_trust_score(agent: Agent, post: Post, weights: FeedWeights) -> float:
    # Trust score may come from source-level trust or author-level trust synced from social graph.
    trust_value = agent.trust_scores.get(post.author_id, agent.trust_scores.get(post.source_type, 0.5))
    return trust_value * weights.source_trust


def social_proximity_score(post: Post, weights: FeedWeights) -> float:
    return _clamp(float(post.metadata.get("social_proximity", 0.0))) * weights.social_proximity


def novelty_score(agent: Agent, post: Post, weights: FeedWeights) -> float:
    return (0.0 if post.post_id in agent.seen_content_ids else 1.0) * weights.novelty


class FeedRanker:
    """Generate ranked feed items with transparent and replaceable scoring components."""

    def __init__(self, weights: FeedWeights, max_items: int = 10, strategy: RankingStrategy = "balanced") -> None:
        self.weights = weights
        self.max_items = max_items
        self.strategy: RankingStrategy = strategy

    def _component_breakdown(self, agent: Agent, post: Post, step: int) -> dict[str, float]:
        base_scores = {
            "heat_score": heat_score(post, self.weights),
            "freshness_score": freshness_score(post, step, self.weights),
            "topic_match_score": topic_match_score(agent, post, self.weights),
            "stance_affinity_score": stance_affinity_score(agent, post, self.weights),
            "official_boost_score": official_boost_score(post, self.weights),
            "source_trust_score": source_trust_score(agent, post, self.weights),
            "social_proximity_score": social_proximity_score(post, self.weights),
            "novelty_score": novelty_score(agent, post, self.weights),
        }
        multipliers = STRATEGY_MULTIPLIERS[self.strategy]
        return {name: round(score * multipliers[name], 4) for name, score in base_scores.items()}

    def _reason_summary(self, breakdown: dict[str, float]) -> str:
        top_components = sorted(breakdown.items(), key=lambda item: item[1], reverse=True)[:3]
        reason = ",".join(f"{name}={value:.2f}" for name, value in top_components)
        return f"strategy={self.strategy};{reason}"

    def rank(self, agent: Agent, posts: dict[str, Post], step: int) -> list[FeedItem]:
        items: list[FeedItem] = []
        for post in posts.values():
            if (post.visibility_scope or post.visibility) not in {"public", "followers_only", "official_global"}:
                continue
            breakdown = self._component_breakdown(agent, post, step)
            score = sum(breakdown.values())
            if post.post_id in agent.seen_content_ids:
                score *= 0.4
            items.append(
                FeedItem(
                    item_id=f"fi_{agent.agent_id}_{post.post_id}",
                    item_type="post",
                    ref_id=post.post_id,
                    score=round(score, 4),
                    reason=self._reason_summary(breakdown),
                    breakdown=breakdown,
                )
            )
        return sorted(items, key=lambda it: it.score, reverse=True)[: self.max_items]
