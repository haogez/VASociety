"""Content pool and platform-level controls."""

from __future__ import annotations

from dataclasses import dataclass, field

from vasociety.models.content import Post


@dataclass(slots=True)
class ContentPoolState:
    trending_pool: list[str] = field(default_factory=list)
    official_pinned_content: list[str] = field(default_factory=list)
    suppressed_content: set[str] = field(default_factory=set)


def build_trending_pool(
    posts: dict[str, Post],
    current_step: int,
    suppressed_content: set[str] | None = None,
    top_k: int = 8,
) -> list[str]:
    suppressed = suppressed_content or set()
    scored: list[tuple[str, float]] = []
    for post_id, post in posts.items():
        if post_id in suppressed:
            continue
        freshness = 1.0 / (1 + max(0, current_step - post.created_at_step))
        engagement = post.likes + 1.2 * post.comments_count + 1.6 * post.reposts
        score = post.heat + 0.35 * freshness + 0.04 * engagement + 0.02 * post.exposure_count
        scored.append((post_id, round(score, 4)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [post_id for post_id, _ in scored[:top_k]]


def apply_suppression(posts: dict[str, Post], suppressed_content: set[str]) -> None:
    for post_id in suppressed_content:
        post = posts.get(post_id)
        if post is None:
            continue
        post.metadata["suppressed"] = True
        post.heat = round(max(0.03, post.heat * 0.65), 4)


def apply_official_pin(posts: dict[str, Post], pinned_content: list[str], boost: float = 0.6) -> None:
    for post_id in pinned_content:
        post = posts.get(post_id)
        if post is None:
            continue
        post.metadata["pinned"] = True
        post.heat = round(post.heat + boost, 4)
