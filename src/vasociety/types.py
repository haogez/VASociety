"""Shared literal types for module contracts."""

from typing import Literal

ActionType = Literal["view", "like", "comment", "repost", "create_post", "skip"]
InterventionType = Literal["inject_news", "inject_fact_check"]
SourceType = Literal["organic", "official", "fact_check"]
ItemType = Literal["post", "comment"]
