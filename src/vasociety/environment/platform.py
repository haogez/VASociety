"""Simplified social platform environment state transitions."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from vasociety.models.content import Comment, Post


class PlatformEnvironment:
    """Mutations over content pool such as heat decay and engagement updates."""

    def __init__(self, heat_decay: float = 0.9) -> None:
        self.heat_decay = heat_decay

    def decay_heat(self, posts: dict[str, Post]) -> None:
        """Decay heat each step while keeping small floor to avoid hard zero."""

        for post in posts.values():
            post.heat = max(0.1, post.heat * self.heat_decay)

    @staticmethod
    def create_snapshot(step: int, posts: dict[str, Post], comments: dict[str, Comment]) -> dict[str, Any]:
        """Small state snapshot for time-series debugging and offline analysis."""

        return {
            "step": step,
            "post_count": len(posts),
            "comment_count": len(comments),
            "top_posts": [asdict(p) for p in sorted(posts.values(), key=lambda x: x.heat, reverse=True)[:3]],
        }
