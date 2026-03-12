"""Belief and stance update utilities for agents."""

from __future__ import annotations

from vasociety.models.agent import Agent
from vasociety.models.content import Post


def update_topic_belief(agent: Agent, post: Post, step: int) -> dict[str, str | float | int]:
    """Apply a lightweight topic belief/stance update and return delta summary."""

    topic = post.topic
    prev_belief = agent.topic_beliefs.get(topic, 0.5)
    trust_multiplier = 1.0 + (0.3 if post.source_type in {"official", "fact_check"} else 0.0)
    direction = -0.12 if post.stance == "corrective" else 0.08
    direction += 0.03 if post.stance in {"questioning", "opposed"} else 0.0
    direction -= agent.skepticism_level * 0.04

    new_belief = min(1.0, max(0.0, prev_belief + direction * trust_multiplier))
    old_stance = agent.topic_stances.get(topic, "neutral")
    if new_belief > 0.62:
        new_stance = "supportive"
    elif new_belief < 0.38:
        new_stance = "questioning"
    else:
        new_stance = "neutral"

    agent.topic_beliefs[topic] = new_belief
    agent.topic_stances[topic] = new_stance
    shifted = old_stance != new_stance
    if shifted:
        agent.stance_update_history.append(
            {"step": step, "topic": topic, "from": old_stance, "to": new_stance, "belief": round(new_belief, 4)}
        )

    return {
        "topic": topic,
        "prev_belief": round(prev_belief, 4),
        "new_belief": round(new_belief, 4),
        "old_stance": old_stance,
        "new_stance": new_stance,
        "stance_shifted": shifted,
    }
