"""Content models for platform objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vasociety.types import SourceType


@dataclass(slots=True)
class Post:
    post_id: str
    author_id: str
    created_at_step: int
    content: str
    topic: str
    stance: str
    source_type: SourceType
    parent_post_id: str | None = None
    origin_post_id: str | None = None
    diffusion_path: list[str] = field(default_factory=list)
    visibility_scope: str = "public"
    visibility: str = "public"
    exposure_count: int = 0
    last_active_step: int | None = None
    heat: float = 1.0
    likes: int = 0
    reposts: int = 0
    comments_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep backward compatibility with older `visibility` field while standardizing scope.
        if self.visibility_scope == "public" and self.visibility != "public":
            self.visibility_scope = self.visibility
        self.visibility = self.visibility_scope


@dataclass(slots=True)
class Comment:
    comment_id: str
    post_id: str
    author_id: str
    created_at_step: int
    content: str
    stance: str


@dataclass(slots=True)
class FeedItem:
    item_id: str
    item_type: str
    ref_id: str
    score: float
    reason: str
    breakdown: dict[str, float] = field(default_factory=dict)
