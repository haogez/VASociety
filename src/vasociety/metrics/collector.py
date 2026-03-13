"""Metric collection for each simulation step."""

from __future__ import annotations

from collections import Counter, defaultdict

from vasociety.models.metrics import MetricsSnapshot
from vasociety.models.state import SimulationState


class MetricsCollector:
    """Compute aggregate indicators from mutable state."""

    @staticmethod
    def collect(state: SimulationState, active_agents: int) -> MetricsSnapshot:
        total_posts = len(state.posts)
        stance_distribution_counter = Counter(post.stance for post in state.posts.values())
        stance_distribution = {
            key: (value / total_posts if total_posts else 0.0)
            for key, value in stance_distribution_counter.items()
        }
        persona_participation = Counter(
            agent.persona_type for agent in state.agents.values() if any(rec.step == state.current_step for rec in agent.action_history)
        )
        per_persona_action_distribution: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for agent in state.agents.values():
            for record in agent.action_history:
                if record.step == state.current_step:
                    per_persona_action_distribution[agent.persona_type][record.action] += 1

        rumor_like = sum(1 for post in state.posts.values() if post.stance in {"uncertain", "questioning", "opposed"})
        corrective = sum(1 for post in state.posts.values() if post.stance == "corrective")
        rumor_actors = {
            record.target_id
            for agent in state.agents.values()
            for record in agent.action_history
            if record.target_id and record.action in {"like", "comment", "repost"}
            and record.target_id in state.posts
            and state.posts[record.target_id].stance in {"uncertain", "questioning", "opposed"}
        }
        corrective_actors = {
            record.target_id
            for agent in state.agents.values()
            for record in agent.action_history
            if record.target_id and record.action in {"like", "comment", "repost"}
            and record.target_id in state.posts
            and state.posts[record.target_id].stance == "corrective"
        }
        topic_heat: dict[str, float] = defaultdict(float)
        for post in state.posts.values():
            topic_heat[post.topic] += post.heat
        intervention_events = [
            item
            for item in state.event_log
            if item.get("event") == "intervention" and int(item.get("step", -1)) == state.current_step
        ]
        intervention_type_counts = Counter(
            str(item.get("payload", {}).get("type", "unknown")) for item in intervention_events
        )
        governance_action_count = sum(
            intervention_type_counts.get(name, 0)
            for name in {"platform_boost", "platform_suppress", "official_pin", "targeted_push"}
        )

        return MetricsSnapshot(
            step=state.current_step,
            total_posts=total_posts,
            total_comments=len(state.comments),
            total_likes=sum(post.likes for post in state.posts.values()),
            total_reposts=sum(post.reposts for post in state.posts.values()),
            discussion_heat=round(sum(post.heat for post in state.posts.values()), 4),
            active_agents=active_agents,
            stance_distribution=stance_distribution,
            persona_participation=dict(persona_participation),
            per_persona_action_distribution={k: dict(v) for k, v in per_persona_action_distribution.items()},
            rumor_like_content_count=rumor_like,
            corrective_content_count=corrective,
            rumor_spread_coverage=round(len(rumor_actors) / total_posts, 4) if total_posts else 0.0,
            corrective_spread_coverage=round(len(corrective_actors) / total_posts, 4) if total_posts else 0.0,
            stance_shift_count=state.stance_shift_count,
            per_step_topic_heat={k: round(v, 4) for k, v in topic_heat.items()},
            intervention_event_count=len(intervention_events),
            governance_action_count=governance_action_count,
            suppressed_content_count=len(state.suppressed_content),
            pinned_content_count=len(state.official_pinned_content),
            intervention_type_counts=dict(intervention_type_counts),
        )
