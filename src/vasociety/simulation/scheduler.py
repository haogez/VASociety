"""Backward-compatible import for intervention scheduler."""

from __future__ import annotations

import random

from vasociety.interventions.scheduler import InterventionScheduler as _InterventionScheduler
from vasociety.models.agent import Agent


class AgentOnlineScheduler:
    """Deterministic online/offline scheduler using activity profiles."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def determine_online_agents(self, agents: dict[str, Agent]) -> list[Agent]:
        online_agents: list[Agent] = []
        for agent_id in sorted(agents):
            agent = agents[agent_id]
            agent.is_online = self._rng.random() < agent.activity_profile
            if agent.is_online:
                online_agents.append(agent)
        return online_agents


InterventionScheduler = _InterventionScheduler

__all__ = ["InterventionScheduler", "AgentOnlineScheduler"]
