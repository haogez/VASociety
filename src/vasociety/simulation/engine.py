"""Main step-based simulation engine for phase-1 demo."""

from __future__ import annotations

import random
from dataclasses import asdict

from vasociety.agents.policy import AgentPolicy, Decision
from vasociety.environment.feed_ranker import FeedRanker
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.metrics.collector import MetricsCollector
from vasociety.models.agent import ActionRecord, Agent
from vasociety.models.content import Comment, Post
from vasociety.models.state import SimulationState
from vasociety.simulation.scheduler import InterventionScheduler


class SimulationEngine:
    """Coordinate environment, feed, policy, actions, and metrics by step."""

    def __init__(
        self,
        state: SimulationState,
        feed_ranker: FeedRanker,
        policy: AgentPolicy,
        scheduler: InterventionScheduler,
        env: PlatformEnvironment,
        intervention_handler: InterventionHandler,
        seed: int,
    ) -> None:
        self.state = state
        self.feed_ranker = feed_ranker
        self.policy = policy
        self.scheduler = scheduler
        self.env = env
        self.intervention_handler = intervention_handler
        self.rng = random.Random(seed)

    def run(self, steps: int, snapshot_each_step: bool = False) -> SimulationState:
        """Run fixed loop for a configured number of steps."""

        for step in range(1, steps + 1):
            self.state.current_step = step
            self._apply_interventions(step)
            self.env.decay_heat(self.state.posts)
            online_agents = self._update_agent_online_status()
            self._run_agent_cycle(online_agents)

            snapshot = MetricsCollector.collect(self.state, active_agents=len(online_agents))
            self.state.metrics_history.append(snapshot)
            self.state.event_log.append({"step": step, "event": "metrics", "payload": asdict(snapshot)})
            if snapshot_each_step:
                self.state.snapshots.append(
                    self.env.create_snapshot(step, posts=self.state.posts, comments=self.state.comments)
                )
        return self.state

    def _apply_interventions(self, step: int) -> None:
        for intervention in self.scheduler.get_for_step(step):
            self.intervention_handler.apply(intervention, self.state)
            self.state.event_log.append(
                {
                    "step": step,
                    "event": "intervention",
                    "payload": {
                        "intervention_id": intervention.intervention_id,
                        "type": intervention.type,
                        "payload": intervention.payload,
                    },
                }
            )

    def _update_agent_online_status(self) -> list[Agent]:
        online: list[Agent] = []
        for agent in self.state.agents.values():
            agent.is_online = self.rng.random() < agent.activity_profile
            if agent.is_online:
                online.append(agent)
        return online

    def _run_agent_cycle(self, online_agents: list[Agent]) -> None:
        for agent in online_agents:
            feed = self.feed_ranker.rank(agent=agent, posts=self.state.posts, step=self.state.current_step)
            decision = self.policy.decide(agent=agent, feed=feed, posts=self.state.posts)
            self._apply_decision(agent, decision)

    def _apply_decision(self, agent: Agent, decision: Decision) -> None:
        action = decision.action
        target_id = decision.target_post_id
        content = decision.content
        stance = decision.stance or "neutral"

        if target_id and target_id in self.state.posts:
            agent.seen_content_ids.add(target_id)

        if action == "like" and target_id:
            self.state.posts[target_id].likes += 1
            self.state.posts[target_id].heat += 0.25
        elif action == "comment" and target_id and content:
            comment_id = f"comment_{len(self.state.comments)+1:05d}"
            self.state.comments[comment_id] = Comment(
                comment_id=comment_id,
                post_id=target_id,
                author_id=agent.agent_id,
                created_at_step=self.state.current_step,
                content=content,
                stance=stance,
            )
            self.state.posts[target_id].comments_count += 1
            self.state.posts[target_id].heat += 0.35
        elif action == "repost" and target_id:
            parent = self.state.posts[target_id]
            self.state.posts[target_id].reposts += 1
            self.state.posts[target_id].heat += 0.4
            post_id = f"post_{len(self.state.posts)+1:05d}"
            self.state.posts[post_id] = Post(
                post_id=post_id,
                author_id=agent.agent_id,
                created_at_step=self.state.current_step,
                content=f"转发：{parent.content}",
                topic=parent.topic,
                stance=parent.stance,
                source_type="organic",
                parent_post_id=target_id,
                heat=1.1,
            )
            agent.created_post_ids.append(post_id)
        elif action == "create_post" and content:
            topic = agent.interest_topics[0]
            post_id = f"post_{len(self.state.posts)+1:05d}"
            self.state.posts[post_id] = Post(
                post_id=post_id,
                author_id=agent.agent_id,
                created_at_step=self.state.current_step,
                content=content,
                topic=topic,
                stance=stance,
                source_type="organic",
                heat=1.0,
            )
            agent.created_post_ids.append(post_id)

        agent.record_action(
            ActionRecord(
                step=self.state.current_step,
                action=action,
                target_id=target_id,
                content=content,
            )
        )
        self.state.event_log.append(
            {
                "step": self.state.current_step,
                "event": "agent_action",
                "payload": {
                    "agent_id": agent.agent_id,
                    "action": action,
                    "target_id": target_id,
                    "content": content,
                },
            }
        )
