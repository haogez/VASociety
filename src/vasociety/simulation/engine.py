"""Main step-based simulation engine for v0.2."""

from __future__ import annotations

from typing import Any

from vasociety.agents.policy import AgentPolicy, Decision
from vasociety.environment.feed_ranker import FeedRanker
from vasociety.environment.platform import PlatformEnvironment
from vasociety.environment.visibility import visible_posts_for_agent
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.metrics.collector import MetricsCollector
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem
from vasociety.models.intervention import Intervention
from vasociety.models.metrics import MetricsSnapshot
from vasociety.models.state import SimulationState
from vasociety.social.graph import ensure_social_graph
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger
from vasociety.simulation.scheduler import AgentOnlineScheduler


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
        online_scheduler: AgentOnlineScheduler | None = None,
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
        self.online_scheduler = online_scheduler or AgentOnlineScheduler(seed)
        ensure_social_graph(self.state, seed=seed)
        self.env.sync_from_state(self.state)

    def run(self, steps: int, snapshot_each_step: bool = False) -> SimulationState:
        for _ in range(max(0, int(steps))):
            self.step(snapshot_each_step=snapshot_each_step)
        return self.state

    def step(self, snapshot_each_step: bool = False) -> None:
        self.state.current_step += 1
        self.run_step(snapshot_each_step=snapshot_each_step)

    def run_step(self, snapshot_each_step: bool = False) -> None:
        self.apply_interventions()
        self.update_environment()
        online_agents = self.determine_online_agents()
        for agent in online_agents:
            feed = self.build_feed(agent)
            decision = self.call_policy(agent, feed)
            self.call_executor(agent, decision)
        metrics = self.collect_metrics(active_agents=len(online_agents))
        self.record_artifacts(metrics=metrics, snapshot_each_step=snapshot_each_step)

    def apply_interventions(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for intervention in self.scheduler.get_for_step(self.state.current_step):
            result = self.intervention_handler.apply(intervention, self.state)
            self.structured_logger.log_intervention(
                state=self.state,
                intervention=intervention,
                result=result,
            )
            records.append(result)
        if records:
            # Governance interventions can mutate pinned/suppressed controls on state.
            # Keep environment controls synchronized before the next environment update.
            self.env.sync_from_state(self.state)
        return records

    def schedule_intervention(self, intervention: Intervention) -> None:
        self.state.interventions.append(intervention)
        self.scheduler.add_intervention(intervention)

    def update_environment(self) -> None:
        self.env.decay_heat(self.state.posts, current_step=self.state.current_step)
        self.env.refresh_content_pool(self.state.posts, current_step=self.state.current_step, state=self.state)

    def determine_online_agents(self) -> list[Agent]:
        return self.online_scheduler.determine_online_agents(self.state.agents)

    def build_feed(self, agent: Agent) -> list[FeedItem]:
        visible_posts = visible_posts_for_agent(agent, self.state.posts, self.state)
        return self.feed_ranker.rank(agent=agent, posts=visible_posts, step=self.state.current_step)

    def call_policy(self, agent: Agent, feed: list[FeedItem]) -> Decision:
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
            reason=decision.decision_reason or decision.reason,
            state_delta=decision.state_delta,
            visible_item_ids=decision.visible_item_ids,
            ranked_reasons=decision.ranked_reasons,
        )
        return decision

    def call_executor(self, agent: Agent, decision: Decision) -> dict[str, Any]:
        return self.action_executor.execute(
            self.state,
            agent,
            decision,
            structured_logger=self.structured_logger,
        )

    def collect_metrics(self, active_agents: int) -> MetricsSnapshot:
        return MetricsCollector.collect(self.state, active_agents=active_agents)

    def record_artifacts(self, metrics: MetricsSnapshot, snapshot_each_step: bool = False) -> None:
        self.state.metrics_history.append(metrics)
        self.structured_logger.log_metrics(self.state, metrics)
        if snapshot_each_step:
            self.snapshot_recorder.record_step_snapshot(self.state)
