"""Belief and stance update utilities for agents."""

from __future__ import annotations

from vasociety.models.agent import Agent
from vasociety.models.content import Post


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _stance_to_scalar(stance: str) -> int:
    mapping = {
        "supportive": 1,
        "neutral": 0,
        "questioning": -1,
        "opposed": -2,
    }
    return mapping.get(stance, 0)


def _inference_direction(post: Post) -> float:
    if post.stance == "corrective":
        return -1.0
    if post.stance in {"questioning", "opposed"}:
        return 0.35
    return 1.0


def update_topic_belief(
    agent: Agent,
    post: Post,
    step: int,
    relevance_score: float = 0.5,
    credibility_score: float = 0.5,
    emotional_trigger_score: float = 0.4,
    stance_conflict_score: float = 0.3,
    social_signal_score: float = 0.4,
) -> dict[str, str | float | int | bool]:
    """Apply a lightweight but structured belief/stance update and return delta summary."""

    topic = post.topic
    prev_belief = agent.topic_beliefs.get(topic, 0.5)
    prev_uncertainty = agent.topic_uncertainty.get(topic, 0.5)

    source_trust = _clamp(agent.trust_scores.get(post.source_type, 0.5))
    evidence_strength = (
        0.04
        + 0.08 * _clamp(credibility_score)
        + 0.06 * _clamp(relevance_score)
        + 0.04 * _clamp(social_signal_score)
        + 0.02 * _clamp(emotional_trigger_score)
        - 0.03 * _clamp(stance_conflict_score)
        + 0.04 * source_trust
    )
    evidence_strength *= 1.0 - agent.skepticism_level * 0.35

    belief_delta = _inference_direction(post) * evidence_strength
    new_belief = _clamp(prev_belief + belief_delta)

    uncertainty_delta = (
        0.08 * _clamp(stance_conflict_score)
        + 0.05 * _clamp(emotional_trigger_score)
        - 0.07 * _clamp(credibility_score)
        - 0.04 * source_trust
        - 0.03 * _clamp(social_signal_score)
    )
    if post.stance == "corrective":
        uncertainty_delta -= 0.02 * _clamp(credibility_score)
    new_uncertainty = _clamp(prev_uncertainty + uncertainty_delta)

    old_stance = agent.topic_stances.get(topic, "neutral")
    support_threshold = 0.62 + new_uncertainty * 0.08
    questioning_threshold = 0.38 - new_uncertainty * 0.08
    if new_belief > support_threshold:
        new_stance = "supportive"
    elif new_belief < questioning_threshold:
        new_stance = "questioning"
    else:
        new_stance = "neutral"

    agent.topic_beliefs[topic] = new_belief
    agent.topic_uncertainty[topic] = new_uncertainty
    agent.topic_stances[topic] = new_stance
    shifted = old_stance != new_stance
    stance_delta = _stance_to_scalar(new_stance) - _stance_to_scalar(old_stance)
    if shifted:
        agent.stance_update_history.append(
            {
                "step": step,
                "topic": topic,
                "from": old_stance,
                "to": new_stance,
                "belief": round(new_belief, 4),
                "uncertainty": round(new_uncertainty, 4),
            }
        )

    return {
        "topic": topic,
        "prev_belief": round(prev_belief, 4),
        "new_belief": round(new_belief, 4),
        "belief_delta": round(new_belief - prev_belief, 4),
        "old_stance": old_stance,
        "new_stance": new_stance,
        "stance_delta": int(stance_delta),
        "prev_uncertainty": round(prev_uncertainty, 4),
        "new_uncertainty": round(new_uncertainty, 4),
        "uncertainty_delta": round(new_uncertainty - prev_uncertainty, 4),
        "stance_shifted": shifted,
    }
