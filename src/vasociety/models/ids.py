"""Identifier helpers for runtime entities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_ID_REGEX_CACHE: dict[str, re.Pattern[str]] = {}


def _id_pattern(prefix: str) -> re.Pattern[str]:
    pattern = _ID_REGEX_CACHE.get(prefix)
    if pattern is None:
        pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
        _ID_REGEX_CACHE[prefix] = pattern
    return pattern


def _next_counter(existing_ids: Iterable[str], prefix: str) -> int:
    pattern = _id_pattern(prefix)
    max_seen = 0
    for item in existing_ids:
        match = pattern.match(str(item))
        if match:
            max_seen = max(max_seen, int(match.group(1)))
    return max_seen + 1


def format_scoped_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:05d}"


@dataclass(slots=True)
class IdCounters:
    next_post: int = 1
    next_comment: int = 1

    def sync(self, post_ids: Iterable[str], comment_ids: Iterable[str]) -> None:
        self.next_post = _next_counter(post_ids, "post")
        self.next_comment = _next_counter(comment_ids, "comment")

    def allocate_post_id(self) -> str:
        value = format_scoped_id("post", self.next_post)
        self.next_post += 1
        return value

    def allocate_comment_id(self) -> str:
        value = format_scoped_id("comment", self.next_comment)
        self.next_comment += 1
        return value
