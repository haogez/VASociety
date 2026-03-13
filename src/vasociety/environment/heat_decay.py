"""Heat and freshness decay helpers for platform environment."""

from __future__ import annotations

from vasociety.models.content import Post


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def apply_heat_decay(
    post: Post,
    current_step: int,
    base_decay: float = 0.9,
    min_heat: float = 0.05,
    freshness_penalty: float = 0.03,
    revival_window: int = 3,
) -> None:
    """Apply freshness-aware heat decay and a lightweight revival rule."""

    age = max(0, current_step - post.created_at_step)
    freshness_factor = _clamp(1.0 - age * freshness_penalty, 0.55, 1.0)
    decayed = max(min_heat, post.heat * base_decay * freshness_factor)

    engagement_score = post.likes + 1.3 * post.comments_count + 1.6 * post.reposts
    previous_score = float(post.metadata.get("last_engagement_score", engagement_score))
    engagement_delta = max(0.0, engagement_score - previous_score)
    post.metadata["last_engagement_score"] = round(engagement_score, 4)

    revived = decayed
    if post.last_active_step is not None and current_step - post.last_active_step <= revival_window and engagement_delta > 0:
        revived += min(0.8, engagement_delta * 0.15)

    post.heat = round(max(min_heat, revived), 4)
