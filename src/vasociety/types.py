"""Shared literal types for module contracts."""

from typing import Literal

ActionType = Literal["view", "like", "comment", "repost", "create_post", "bookmark", "follow", "skip"]
InterventionType = Literal[
    "inject_news",
    "inject_fact_check",
    "platform_boost",
    "platform_suppress",
    "official_pin",
    "targeted_push",
]
SourceType = Literal["organic", "official", "fact_check"]
ItemType = Literal["post", "comment"]
