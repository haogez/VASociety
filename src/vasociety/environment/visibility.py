"""Visibility rules for filtering candidate content."""

from __future__ import annotations

from vasociety.models.agent import Agent
from vasociety.models.content import Post


def visible_posts_for_agent(agent: Agent, posts: dict[str, Post]) -> dict[str, Post]:
    """Phase-1 rule: public posts are visible to everyone."""

    _ = agent
    return {post_id: post for post_id, post in posts.items() if post.visibility == "public"}
