"""Lightweight social graph construction."""

from __future__ import annotations

import random

from vasociety.models.agent import Agent
from vasociety.models.state import SimulationState
from vasociety.social.community import assign_community_labels
from vasociety.social.trust import sync_agent_trust_scores


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _affinity_score(source: Agent, target: Agent) -> float:
    shared_topics = len(set(source.interest_topics) & set(target.interest_topics))
    topic_affinity = shared_topics / max(1, len(set(source.interest_topics) | set(target.interest_topics)))
    persona_bonus = 0.15 if source.persona_type == target.persona_type else 0.0
    skepticism_distance = abs(source.skepticism_level - target.skepticism_level)
    emotion_distance = abs(source.emotionality_level - target.emotionality_level)
    style_penalty = 0.2 * skepticism_distance + 0.15 * emotion_distance
    return _clamp(0.35 + 0.5 * topic_affinity + persona_bonus - style_penalty)


def initialize_social_graph(
    state: SimulationState,
    seed: int,
    min_followees: int = 2,
    max_followees: int = 6,
) -> None:
    """Initialize follow, trust, affinity and community labels."""

    rng = random.Random(seed + 101)
    agent_ids = list(state.agents.keys())
    if len(agent_ids) < 2:
        state.followees.clear()
        state.followers.clear()
        state.trust_edges.clear()
        state.affinity_edges.clear()
        state.community_labels = {agent_id: "cluster_general" for agent_id in agent_ids}
        return

    followees: dict[str, list[str]] = {}
    followers: dict[str, list[str]] = {agent_id: [] for agent_id in agent_ids}
    trust_edges: dict[str, dict[str, float]] = {}
    affinity_edges: dict[str, dict[str, float]] = {}

    for agent_id in agent_ids:
        source = state.agents[agent_id]
        candidates = [target_id for target_id in agent_ids if target_id != agent_id]
        scored = []
        for target_id in candidates:
            affinity = _affinity_score(source, state.agents[target_id])
            scored.append((target_id, affinity + rng.uniform(0.0, 0.2), affinity))
        scored.sort(key=lambda item: item[1], reverse=True)

        target_count = min(max_followees, max(min_followees, min(len(candidates), 2 + len(source.interest_topics) // 2)))
        selected = [target_id for target_id, _, _ in scored[:target_count]]
        followees[agent_id] = selected

        affinity_edges[agent_id] = {}
        trust_edges[agent_id] = {}
        for target_id, _, affinity in scored[:target_count]:
            followers[target_id].append(agent_id)
            affinity_edges[agent_id][target_id] = round(affinity, 4)
            trust_edges[agent_id][target_id] = round(_clamp(0.35 + 0.5 * affinity + rng.uniform(0.0, 0.1)), 4)

    state.followees.clear()
    state.followees.update(followees)
    state.followers.clear()
    state.followers.update({key: sorted(set(value)) for key, value in followers.items()})
    state.trust_edges.clear()
    state.trust_edges.update(trust_edges)
    state.affinity_edges.clear()
    state.affinity_edges.update(affinity_edges)
    state.community_labels.clear()
    state.community_labels.update(assign_community_labels(state.agents, state.followees))
    sync_agent_trust_scores(state)


def ensure_social_graph(state: SimulationState, seed: int) -> None:
    if state.followees and state.trust_edges:
        if not state.followers:
            followers: dict[str, list[str]] = {agent_id: [] for agent_id in state.agents}
            for source_id, targets in state.followees.items():
                for target_id in targets:
                    followers.setdefault(target_id, []).append(source_id)
            state.followers.clear()
            state.followers.update({key: sorted(set(value)) for key, value in followers.items()})
        if not state.community_labels:
            state.community_labels.update(assign_community_labels(state.agents, state.followees))
        sync_agent_trust_scores(state)
        return
    initialize_social_graph(state, seed=seed)
