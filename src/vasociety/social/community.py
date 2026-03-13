"""Simplified community labeling helpers."""

from __future__ import annotations

from collections import Counter

from vasociety.models.agent import Agent


def assign_community_labels(agents: dict[str, Agent], followees: dict[str, list[str]]) -> dict[str, str]:
    """Assign lightweight cluster labels using neighborhood topic preference."""

    labels: dict[str, str] = {}
    for agent_id, agent in agents.items():
        topic_counter: Counter[str] = Counter(agent.interest_topics)
        for neighbor_id in followees.get(agent_id, []):
            neighbor = agents.get(neighbor_id)
            if neighbor is None:
                continue
            topic_counter.update(neighbor.interest_topics[:1])
        dominant_topic = topic_counter.most_common(1)[0][0] if topic_counter else "general"
        labels[agent_id] = f"cluster_{dominant_topic}"
    return labels


def community_summary(labels: dict[str, str]) -> dict[str, int]:
    counter: Counter[str] = Counter(labels.values())
    return dict(counter)
