"""Main step-based simulation engine for v0.2."""

from __future__ import annotations

import random
from dataclasses import asdict

from vasociety.agents.policy import AgentPolicy
from vasociety.environment.feed_ranker import FeedRanker
from vasociety.environment.platform import PlatformEnvironment
from vasociety.environment.visibility import visible_posts_for_agent
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.metrics.collector import MetricsCollector
from vasociety.models.agent import Agent
from vasociety.models.state import SimulationState
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


class SimulationEngine:
    """Coordinate engine modules and run deterministic step loops."""

    def __init__(
        self,
        state: SimulationState,
        feed_ranker: FeedRanker,
        policy: AgentPolicy,
        scheduler: InterventionScheduler,
        env: PlatformEnvironment,
        intervention_handler: InterventionHandler,
        action_executor: ActionExecutor,
        snapshot_recorder: SnapshotRecorder,
        structured_logger: StructuredEventLogger,
        seed: int,
    ) -> None:
        self.state = state
        self.feed_ranker = feed_ranker
        self.policy = policy
        self.scheduler = scheduler
        self.env = env
        self.intervention_handler = intervention_handler
        self.action_executor = action_executor
        self.snapshot_recorder = snapshot_recorder
        self.structured_logger = structured_logger
        self.rng = random.Random(seed)

    def run(self, steps: int, snapshot_each_step: bool = False) -> SimulationState:
        for step in range(1, steps + 1):
            self.state.current_step = step
            self._apply_interventions()
            self.env.decay_heat(self.state.posts)
            online_agents = self._update_online_agents()
            self._process_online_agents(online_agents)

            snapshot = MetricsCollector.collect(self.state, active_agents=len(online_agents))
            self.state.metrics_history.append(snapshot)
            self.state.event_log.append({"step": step, "event": "metrics", "payload": asdict(snapshot)})

            if snapshot_each_step:
                self.snapshot_recorder.record_step_snapshot(self.state)
        return self.state

    def _apply_interventions(self) -> None:
        for intervention in self.scheduler.get_for_step(self.state.current_step):
            result = self.intervention_handler.apply(intervention, self.state)
            self.state.event_log.append(
                {
                    "step": self.state.current_step,
                    "event": "intervention",
                    "payload": {
                        "intervention_id": intervention.intervention_id,
                        "type": intervention.type,
                        "payload": intervention.payload,
                        "result": result,
                    },
                }
            )

    def _update_online_agents(self) -> list[Agent]:
        online_agents: list[Agent] = []
        for agent in self.state.agents.values():
            agent.is_online = self.rng.random() < agent.activity_profile
            if agent.is_online:
                online_agents.append(agent)
        return online_agents

    def _process_online_agents(self, online_agents: list[Agent]) -> None:
        for agent in online_agents:
            visible_posts = visible_posts_for_agent(agent, self.state.posts)
            feed = self.feed_ranker.rank(agent=agent, posts=visible_posts, step=self.state.current_step)
            decision = self.policy.decide(agent=agent, feed=feed, posts=self.state.posts, step=self.state.current_step)
            self.structured_logger.log_perception(
                self.state,
                agent.agent_id,
                visible_item_ids=decision.visible_item_ids,
                ranked_reasons=decision.ranked_reasons,
            )
            self.structured_logger.log_decision(
                self.state,
                agent.agent_id,
                selected_action=decision.action,
                target_id=decision.target_post_id,
                reason=decision.reason,
                state_delta=decision.state_delta,
            )
            self.action_executor.execute(self.state, agent, decision)
