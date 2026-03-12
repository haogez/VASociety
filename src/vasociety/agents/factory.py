"""Factory helpers to generate agent populations."""

from __future__ import annotations

import random

from vasociety.agents.templates import PERSONA_TEMPLATES
from vasociety.models.agent import Agent


class AgentFactory:
    """Create agents from persona templates with deterministic randomness."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def create_population(self, count: int, topics: list[str]) -> dict[str, Agent]:
        """Create a mixed population cycling through known templates."""

        personas = list(PERSONA_TEMPLATES.keys())
        agents: dict[str, Agent] = {}
        for idx in range(count):
            persona_type = personas[idx % len(personas)]
            attrs = PERSONA_TEMPLATES[persona_type]
            interests = self._rng.sample(topics, k=min(len(topics), 2))
            agent = Agent(
                agent_id=f"agent_{idx:03d}",
                name=f"Agent-{idx:03d}",
                persona_type=persona_type,
                interest_topics=interests,
                current_focus_topics=list(interests),
                **attrs,
            )
            agents[agent.agent_id] = agent
        return agents
