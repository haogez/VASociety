"""Trust-edge synchronization and updates."""

from __future__ import annotations

from vasociety.models.state import SimulationState


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def sync_agent_trust_scores(state: SimulationState) -> None:
    """Sync agent-local trust_scores with social trust edges."""

    for agent_id, agent in state.agents.items():
        edge_map = state.trust_edges.get(agent_id, {})
        for target_id, score in edge_map.items():
            agent.trust_scores[target_id] = round(float(score), 4)
        # Preserve source-level trust defaults.
        agent.trust_scores.setdefault("official", 0.6)
        agent.trust_scores.setdefault("organic", 0.5)
        agent.trust_scores.setdefault("fact_check", 0.7)


def update_trust_by_interaction(
    state: SimulationState,
    actor_id: str,
    target_author_id: str,
    action: str,
    stance_conflict: float,
    interaction_count: int = 1,
) -> dict[str, float]:
    """Update directed trust edge after one interaction."""

    if actor_id == target_author_id:
        return {"prev": 0.0, "new": 0.0, "delta": 0.0}

    action_gain = {
        "like": 0.012,
        "comment": 0.02,
        "repost": 0.03,
    }.get(action, 0.0)
    frequency_multiplier = 1.0 + min(5, max(0, interaction_count - 1)) * 0.12
    conflict_penalty = 0.03 * _clamp(stance_conflict)
    delta = action_gain * frequency_multiplier - conflict_penalty

    source_edges = state.trust_edges.setdefault(actor_id, {})
    prev = float(source_edges.get(target_author_id, 0.5))
    new_value = _clamp(prev + delta)
    source_edges[target_author_id] = round(new_value, 4)

    # Slight reciprocal effect to avoid one-way lock-in.
    reciprocal_edges = state.trust_edges.setdefault(target_author_id, {})
    reciprocal_prev = float(reciprocal_edges.get(actor_id, 0.5))
    reciprocal_edges[actor_id] = round(_clamp(reciprocal_prev + delta * 0.2), 4)

    sync_agent_trust_scores(state)
    return {"prev": round(prev, 4), "new": round(new_value, 4), "delta": round(new_value - prev, 4)}
