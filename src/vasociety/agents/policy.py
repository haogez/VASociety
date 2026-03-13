"""Rule-based cognitive policy with explicit perception and belief pipeline."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from vasociety.agents.belief import update_topic_belief
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post
from vasociety.types import ActionType


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class ContentEvaluation:
    ref_id: str
    topic: str
    relevance_score: float
    credibility_score: float
    emotional_trigger_score: float
    stance_conflict_score: float
    social_signal_score: float
    aggregate_score: float
    is_seen: bool = False

    def to_dict(self) -> dict[str, float | str | bool]:
        return {
            "ref_id": self.ref_id,
            "topic": self.topic,
            "relevance_score": round(self.relevance_score, 4),
            "credibility_score": round(self.credibility_score, 4),
            "emotional_trigger_score": round(self.emotional_trigger_score, 4),
            "stance_conflict_score": round(self.stance_conflict_score, 4),
            "social_signal_score": round(self.social_signal_score, 4),
            "aggregate_score": round(self.aggregate_score, 4),
            "is_seen": self.is_seen,
        }


@dataclass(slots=True)
class Decision:
    action: ActionType
    target_post_id: str | None = None
    content: str | None = None
    stance: str | None = None
    reason: str = ""
    decision_reason: str = ""
    visible_item_ids: list[str] = field(default_factory=list)
    ranked_reasons: list[dict[str, Any]] = field(default_factory=list)
    state_delta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision_reason and not self.reason:
            self.reason = self.decision_reason
        elif self.reason and not self.decision_reason:
            self.decision_reason = self.reason


class AgentPolicy:
    """Deterministic pseudo-random rule set based on a structured cognition pipeline."""

    def __init__(self, seed: int, view_top_k: int = 3) -> None:
        self._rng = random.Random(seed)
        self.view_top_k = view_top_k

    def perceive(
        self, agent: Agent, feed: list[FeedItem]
    ) -> tuple[list[FeedItem], list[str], list[dict[str, Any]]]:
        visible = feed[: self.view_top_k]
        visible_ids = [item.ref_id for item in visible]
        ranked_reasons: list[dict[str, Any]] = [
            {"ref_id": item.ref_id, "score": item.score, "reason": item.reason, "breakdown": item.breakdown}
            for item in visible
        ]
        return visible, visible_ids, ranked_reasons

    def evaluate_content(self, agent: Agent, visible: list[FeedItem], posts: dict[str, Post]) -> list[ContentEvaluation]:
        evaluations: list[ContentEvaluation] = []
        for item in visible:
            post = posts[item.ref_id]
            relevance = self._score_relevance(agent, post)
            credibility = self._score_credibility(agent, post, item)
            emotional_trigger = self._score_emotional_trigger(agent, post)
            stance_conflict = self._score_stance_conflict(agent, post)
            social_signal = self._score_social_signal(post, item)
            novelty_bonus = -0.12 if post.post_id in agent.seen_content_ids else 0.04
            aggregate = (
                0.30 * relevance
                + 0.24 * credibility
                + 0.18 * emotional_trigger
                + 0.16 * social_signal
                - 0.16 * stance_conflict
                + novelty_bonus
            )
            evaluations.append(
                ContentEvaluation(
                    ref_id=post.post_id,
                    topic=post.topic,
                    relevance_score=_clamp(relevance),
                    credibility_score=_clamp(credibility),
                    emotional_trigger_score=_clamp(emotional_trigger),
                    stance_conflict_score=_clamp(stance_conflict),
                    social_signal_score=_clamp(social_signal),
                    aggregate_score=round(max(0.0, aggregate), 4),
                    is_seen=post.post_id in agent.seen_content_ids,
                )
            )
        return evaluations

    def update_beliefs(
        self,
        agent: Agent,
        evaluations: list[ContentEvaluation],
        posts: dict[str, Post],
        step: int,
    ) -> dict[str, Any]:
        belief_delta: dict[str, float] = {}
        stance_delta: dict[str, int] = {}
        uncertainty_delta: dict[str, float] = {}
        stance_shifts: list[dict[str, Any]] = []

        for evaluation in evaluations:
            post = posts[evaluation.ref_id]
            result = update_topic_belief(
                agent=agent,
                post=post,
                step=step,
                relevance_score=evaluation.relevance_score,
                credibility_score=evaluation.credibility_score,
                emotional_trigger_score=evaluation.emotional_trigger_score,
                stance_conflict_score=evaluation.stance_conflict_score,
                social_signal_score=evaluation.social_signal_score,
            )
            topic = str(result["topic"])
            belief_delta[topic] = round(belief_delta.get(topic, 0.0) + float(result["belief_delta"]), 4)
            uncertainty_delta[topic] = round(
                uncertainty_delta.get(topic, 0.0) + float(result["uncertainty_delta"]),
                4,
            )
            if int(result["stance_delta"]) != 0:
                stance_delta[topic] = stance_delta.get(topic, 0) + int(result["stance_delta"])
            if bool(result["stance_shifted"]):
                stance_shifts.append(
                    {
                        "topic": topic,
                        "from": str(result["old_stance"]),
                        "to": str(result["new_stance"]),
                        "belief": float(result["new_belief"]),
                    }
                )

        return {
            "belief_delta": belief_delta,
            "stance_delta": stance_delta,
            "uncertainty_delta": uncertainty_delta,
            "stance_shifted": bool(stance_shifts),
            "stance_shifts": stance_shifts,
            "evaluated_items": len(evaluations),
        }

    def assess_social_pressure(
        self,
        agent: Agent,
        evaluations: list[ContentEvaluation],
        posts: dict[str, Post],
    ) -> dict[str, float | str]:
        if not evaluations:
            return {"pressure_score": 0.0, "dominant_stance": "neutral", "cohesion": 0.0}

        stance_support: dict[str, float] = {}
        pressure_signal = 0.0
        for evaluation in evaluations:
            post = posts[evaluation.ref_id]
            weight = 0.45 + evaluation.social_signal_score * 0.55
            stance_support[post.stance] = stance_support.get(post.stance, 0.0) + weight
            alignment = 1.0 - evaluation.stance_conflict_score
            pressure_signal += (alignment - 0.5) * 2.0 * weight

        dominant_stance = max(stance_support.items(), key=lambda item: item[1])[0]
        cohesion = max(stance_support.values()) / max(0.001, sum(stance_support.values()))
        pressure_score = _clamp((pressure_signal / max(1, len(evaluations))) * agent.conformity_level, -1.0, 1.0)
        return {
            "pressure_score": round(pressure_score, 4),
            "dominant_stance": dominant_stance,
            "cohesion": round(cohesion, 4),
        }

    def decide_action(
        self,
        agent: Agent,
        evaluations: list[ContentEvaluation],
        posts: dict[str, Post],
        social_pressure: dict[str, float | str],
    ) -> Decision:
        if not evaluations:
            return self._maybe_create_post(agent, None, decision_reason="empty_feed")

        unseen = [item for item in evaluations if not item.is_seen]
        if not unseen:
            return Decision(action="skip", decision_reason="all_seen")

        pressure_score = float(social_pressure.get("pressure_score", 0.0))
        adjusted_candidates: list[tuple[ContentEvaluation, float]] = []
        for evaluation in unseen:
            pressure_term = pressure_score * (1.0 - evaluation.stance_conflict_score) * 0.15
            emotion_term = self._emotion_reactivity(agent.current_emotion)
            adjusted = (
                evaluation.aggregate_score
                + pressure_term
                + 0.06 * agent.expression_level
                + emotion_term
                - 0.04 * agent.skepticism_level
            )
            adjusted_candidates.append((evaluation, round(adjusted, 4)))

        adjusted_candidates.sort(key=lambda pair: pair[1], reverse=True)
        selected_eval, selected_score = adjusted_candidates[0]
        selected_post = posts[selected_eval.ref_id]
        top_k_scores = [score for _, score in adjusted_candidates[: max(1, min(3, len(adjusted_candidates)))]]
        perception_summary_score = sum(top_k_scores) / len(top_k_scores)
        engagement_drive = (
            0.45 * selected_score
            + 0.25 * perception_summary_score
            + 0.16 * agent.expression_level
            + 0.08 * (1.0 - agent.skepticism_level)
            + 0.06 * max(0.0, pressure_score)
        )

        roll = self._rng.random()
        if engagement_drive > 0.95 and roll < 0.35 + agent.expression_level * 0.2:
            return Decision(
                action="repost",
                target_post_id=selected_post.post_id,
                decision_reason="high_drive_repost",
            )
        if engagement_drive > 0.70 and roll < 0.78:
            return Decision(
                action="comment",
                target_post_id=selected_post.post_id,
                content=self._make_comment(agent, selected_post),
                stance=self._derive_stance(agent, selected_post, selected_eval),
                decision_reason="medium_drive_comment",
            )
        if engagement_drive > 0.48:
            return Decision(
                action="like",
                target_post_id=selected_post.post_id,
                decision_reason="low_drive_like",
            )
        if roll < max(0.05, agent.expression_level * 0.22):
            return self._maybe_create_post(agent, selected_post.topic, decision_reason="self_expression")
        return Decision(
            action="skip",
            target_post_id=selected_post.post_id,
            decision_reason="insufficient_drive",
        )

    def decide(self, agent: Agent, feed: list[FeedItem], posts: dict[str, Post], step: int) -> Decision:
        visible, visible_ids, ranked_reasons = self.perceive(agent, feed)
        evaluations = self.evaluate_content(agent, visible, posts)
        belief_delta = self.update_beliefs(agent, evaluations, posts, step)
        social_pressure = self.assess_social_pressure(agent, evaluations, posts)
        emotion = self._update_emotion(agent, evaluations, social_pressure)
        decision = self.decide_action(agent, evaluations, posts, social_pressure)
        decision.visible_item_ids = visible_ids

        evaluation_by_ref = {item.ref_id: item for item in evaluations}
        enriched_reasons: list[dict[str, Any]] = []
        for reason in ranked_reasons:
            evaluation = evaluation_by_ref.get(str(reason["ref_id"]))
            enriched = dict(reason)
            if evaluation is not None:
                enriched["evaluation"] = evaluation.to_dict()
            enriched_reasons.append(enriched)
        decision.ranked_reasons = enriched_reasons
        decision.state_delta = {
            **belief_delta,
            "social_pressure": social_pressure,
            "emotion": emotion,
        }
        if not decision.reason:
            decision.reason = decision.decision_reason
        if not decision.decision_reason:
            decision.decision_reason = decision.reason
        return decision

    def _maybe_create_post(self, agent: Agent, topic: str | None, decision_reason: str) -> Decision:
        if self._rng.random() < agent.expression_level * 0.25:
            chosen_topic = topic or self._rng.choice(agent.interest_topics)
            stance = agent.topic_stances.get(chosen_topic, "questioning")
            return Decision(
                action="create_post",
                content=f"关于{chosen_topic}，我目前更偏向{stance}，仍在持续观察。",
                stance=stance,
                decision_reason=decision_reason,
            )
        return Decision(action="skip", decision_reason=decision_reason)

    def _update_emotion(
        self,
        agent: Agent,
        evaluations: list[ContentEvaluation],
        social_pressure: dict[str, float | str],
    ) -> str:
        if not evaluations:
            agent.current_emotion = "calm"
            return agent.current_emotion

        avg_trigger = sum(item.emotional_trigger_score for item in evaluations) / len(evaluations)
        avg_conflict = sum(item.stance_conflict_score for item in evaluations) / len(evaluations)
        pressure = abs(float(social_pressure.get("pressure_score", 0.0)))
        stress = 0.45 * avg_trigger + 0.35 * avg_conflict + 0.20 * pressure

        if stress < 0.25:
            emotion = "calm"
        elif stress < 0.45:
            emotion = "neutral"
        elif stress < 0.65:
            emotion = "alert"
        elif float(social_pressure.get("pressure_score", 0.0)) < -0.1:
            emotion = "anxious"
        else:
            emotion = "angry"
        agent.current_emotion = emotion
        return emotion

    @staticmethod
    def _score_relevance(agent: Agent, post: Post) -> float:
        relevance = 0.35
        if post.topic in agent.interest_topics:
            relevance += 0.55
        if post.topic in agent.current_focus_topics:
            relevance += 0.1
        return _clamp(relevance)

    @staticmethod
    def _score_credibility(agent: Agent, post: Post, item: FeedItem) -> float:
        source_trust = _clamp(agent.trust_scores.get(post.source_type, 0.5))
        official_bonus = 0.15 if post.source_type in {"official", "fact_check"} else 0.0
        feed_hint = _clamp(item.breakdown.get("source_trust_score", 0.0) * 0.2)
        return _clamp(0.2 + 0.55 * source_trust + official_bonus + feed_hint)

    @staticmethod
    def _score_emotional_trigger(agent: Agent, post: Post) -> float:
        stance_base = {
            "uncertain": 0.55,
            "questioning": 0.62,
            "opposed": 0.72,
            "corrective": 0.38,
            "supportive": 0.45,
        }.get(post.stance, 0.45)
        return _clamp(stance_base * (0.65 + 0.75 * agent.emotionality_level) + min(0.18, post.heat * 0.05))

    @staticmethod
    def _score_stance_conflict(agent: Agent, post: Post) -> float:
        topic_stance = agent.topic_stances.get(post.topic, "neutral")
        if topic_stance == post.stance:
            return 0.0
        if topic_stance == "neutral" or post.stance == "neutral":
            return 0.35
        if {topic_stance, post.stance} == {"supportive", "corrective"}:
            return 0.85
        if {topic_stance, post.stance} == {"supportive", "questioning"}:
            return 0.72
        if {topic_stance, post.stance} == {"questioning", "corrective"}:
            return 0.45
        return 0.6

    @staticmethod
    def _score_social_signal(post: Post, item: FeedItem) -> float:
        heat_term = min(1.0, post.heat / 3.0)
        engagement_term = min(1.0, (post.likes + post.reposts + post.comments_count) / 10.0)
        feed_social = _clamp(item.breakdown.get("social_proximity_score", 0.0))
        return _clamp(0.45 * heat_term + 0.35 * engagement_term + 0.20 * feed_social)

    @staticmethod
    def _emotion_reactivity(emotion: str) -> float:
        if emotion == "angry":
            return 0.1
        if emotion == "anxious":
            return 0.06
        if emotion == "alert":
            return 0.04
        if emotion == "calm":
            return -0.08
        return 0.0

    @staticmethod
    def _make_comment(agent: Agent, post: Post) -> str:
        emotion = agent.current_emotion
        if post.source_type == "fact_check":
            return "如果辟谣属实，那之前的信息可能有误。"
        if emotion == "angry":
            return "这个话题已经影响很大了，平台应该尽快给出更多信息。"
        if emotion == "anxious":
            return "信息有点混乱，我担心还会继续发酵。"
        if emotion == "alert":
            return "这个消息值得持续跟进，先保留判断。"
        if agent.emotionality_level > 0.7:
            return "这件事太离谱了，我觉得需要继续关注。"
        return "我倾向于相信这个消息，但还需要更多证据。"

    @staticmethod
    def _derive_stance(agent: Agent, post: Post, evaluation: ContentEvaluation) -> str:
        topic_stance = agent.topic_stances.get(post.topic, "neutral")
        if topic_stance != "neutral":
            return topic_stance
        if post.stance == "corrective" and evaluation.credibility_score > 0.6:
            return "questioning"
        if agent.conformity_level > 0.58 and evaluation.stance_conflict_score < 0.5:
            return post.stance
        return "questioning"
