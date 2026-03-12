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
        personas = list(PERSONA_TEMPLATES.keys())
        agents: dict[str, Agent] = {}
        for idx in range(count):
            persona_type = personas[idx % len(personas)]
            attrs = PERSONA_TEMPLATES[persona_type]
            interests = self._rng.sample(topics, k=min(len(topics), 2))
            topic_beliefs = {topic: round(self._rng.uniform(0.35, 0.65), 3) for topic in topics}
            topic_stances = {
                topic: ("supportive" if belief > 0.58 else "questioning" if belief < 0.42 else "neutral")
                for topic, belief in topic_beliefs.items()
            }
            trust_scores = {"official": round(attrs["authority_trust_level"], 3), "organic": 0.5}
            agent = Agent(
                agent_id=f"agent_{idx:03d}",
                name=f"Agent-{idx:03d}",
                persona_type=persona_type,
                interest_topics=interests,
                current_focus_topics=list(interests),
                topic_beliefs=topic_beliefs,
                topic_stances=topic_stances,
                trust_scores=trust_scores,
                **attrs,
            )
            agents[agent.agent_id] = agent
        return agents
