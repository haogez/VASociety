"""Metric collection for each simulation step."""

from __future__ import annotations

from collections import Counter

from vasociety.models.state import MetricsSnapshot, SimulationState


class MetricsCollector:
    """Compute aggregate indicators from the mutable state."""

    @staticmethod
    def collect(state: SimulationState, active_agents: int) -> MetricsSnapshot:
        stances = Counter(post.stance for post in state.posts.values())
        total_posts = len(state.posts)
        stance_distribution = {
            stance: (count / total_posts if total_posts else 0.0) for stance, count in stances.items()
        }
        total_likes = sum(p.likes for p in state.posts.values())
        total_reposts = sum(p.reposts for p in state.posts.values())
        discussion_heat = round(sum(p.heat for p in state.posts.values()), 4)
        return MetricsSnapshot(
            step=state.current_step,
            total_posts=total_posts,
            total_comments=len(state.comments),
            total_likes=total_likes,
            total_reposts=total_reposts,
            stance_distribution=stance_distribution,
            discussion_heat=discussion_heat,
            active_agents=active_agents,
        )
