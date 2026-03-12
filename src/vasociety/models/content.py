"""Content models for platform objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vasociety.types import SourceType


@dataclass(slots=True)
class Post:
    """Post object in the simulated platform."""

    post_id: str
    author_id: str
    created_at_step: int
    content: str
    topic: str
    stance: str
    source_type: SourceType
    parent_post_id: str | None = None
    visibility: str = "public"
    heat: float = 1.0
    likes: int = 0
    reposts: int = 0
    comments_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Comment:
    """Comment object linked to a post."""

    comment_id: str
    post_id: str
    author_id: str
    created_at_step: int
    content: str
    stance: str


@dataclass(slots=True)
class FeedItem:
    """One ranked item surfaced in an agent feed."""

    item_id: str
    item_type: str
    ref_id: str
    score: float
    reason: str
