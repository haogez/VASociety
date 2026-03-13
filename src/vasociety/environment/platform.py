"""Platform environment with lifecycle and content-pool rules."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from vasociety.environment.content_pool import (
    ContentPoolState,
    apply_official_pin,
    apply_suppression,
    build_trending_pool,
)
from vasociety.environment.heat_decay import apply_heat_decay
from vasociety.models.content import Comment, Post
from vasociety.models.state import SimulationState


class PlatformEnvironment:
    """Mutations over content pool including lifecycle, trends and governance hooks."""

    def __init__(
        self,
        heat_decay: float = 0.9,
        min_heat: float = 0.05,
        freshness_penalty: float = 0.03,
        revival_window: int = 3,
        trending_top_k: int = 8,
    ) -> None:
        self.heat_decay = heat_decay
        self.min_heat = min_heat
        self.freshness_penalty = freshness_penalty
        self.revival_window = revival_window
        self.trending_top_k = trending_top_k
        self.content_pool = ContentPoolState()

    def decay_heat(self, posts: dict[str, Post], current_step: int = 0) -> None:
        """Decay post heat with freshness and revival rule."""

        for post in posts.values():
            apply_heat_decay(
                post=post,
                current_step=current_step,
                base_decay=self.heat_decay,
                min_heat=self.min_heat,
                freshness_penalty=self.freshness_penalty,
                revival_window=self.revival_window,
            )

    def refresh_content_pool(self, posts: dict[str, Post], current_step: int, state: SimulationState | None = None) -> None:
        """Refresh trending/pinned/suppressed state and optionally sync to RuntimeState."""

        apply_suppression(posts, self.content_pool.suppressed_content)
        apply_official_pin(posts, self.content_pool.official_pinned_content)
        self.content_pool.trending_pool = build_trending_pool(
            posts=posts,
            current_step=current_step,
            suppressed_content=self.content_pool.suppressed_content,
            top_k=self.trending_top_k,
        )
        if state is not None:
            state.trending_pool[:] = list(self.content_pool.trending_pool)
            state.official_pinned_content[:] = list(self.content_pool.official_pinned_content)
            state.suppressed_content[:] = sorted(self.content_pool.suppressed_content)

    def sync_from_state(self, state: SimulationState) -> None:
        """Keep environment controls aligned with serializable runtime state."""

        if state.official_pinned_content:
            self.content_pool.official_pinned_content = list(dict.fromkeys(state.official_pinned_content))
        if state.suppressed_content:
            self.content_pool.suppressed_content = set(state.suppressed_content)

    def pin_official_content(self, post_id: str) -> None:
        if post_id not in self.content_pool.official_pinned_content:
            self.content_pool.official_pinned_content.append(post_id)

    def suppress_content(self, post_id: str) -> None:
        self.content_pool.suppressed_content.add(post_id)

    @staticmethod
    def create_snapshot(step: int, posts: dict[str, Post], comments: dict[str, Comment], state: SimulationState | None = None) -> dict[str, Any]:
        """State snapshot for replay and analysis."""

        snapshot = {
            "step": step,
            "post_count": len(posts),
            "comment_count": len(comments),
            "top_posts": [asdict(p) for p in sorted(posts.values(), key=lambda x: x.heat, reverse=True)[:5]],
        }
        if state is not None:
            snapshot["platform_state"] = {
                "trending_pool": list(state.trending_pool),
                "official_pinned_content": list(state.official_pinned_content),
                "suppressed_content": list(state.suppressed_content),
            }
        return snapshot
