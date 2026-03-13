"""Visibility rules for filtering candidate content with social priors."""

from __future__ import annotations

from dataclasses import replace

from vasociety.models.agent import Agent
from vasociety.models.content import Post
from vasociety.models.state import SimulationState


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _social_proximity(agent: Agent, post: Post, state: SimulationState) -> float:
    if post.author_id == agent.agent_id:
        return 1.0

    followees = set(state.followees.get(agent.agent_id, []))
    trust_score = state.trust_edges.get(agent.agent_id, {}).get(post.author_id, 0.0)
    affinity_score = state.affinity_edges.get(agent.agent_id, {}).get(post.author_id, 0.0)
    chain_related = bool(post.parent_post_id and post.parent_post_id in agent.seen_content_ids) or any(
        node in agent.seen_content_ids for node in post.diffusion_path
    )

    proximity = 0.0
    if post.author_id in followees:
        proximity += 0.55
    if chain_related:
        proximity += 0.22
    proximity += 0.25 * trust_score
    proximity += 0.12 * affinity_score
    return _clamp(proximity)


def _is_scope_visible(agent: Agent, post: Post, state: SimulationState) -> bool:
    scope = post.visibility_scope or post.visibility
    if scope == "official_global":
        return True
    if scope == "followers_only":
        if post.author_id == agent.agent_id:
            return True
        return agent.agent_id in set(state.followers.get(post.author_id, []))
    if scope == "public":
        return True
    # Future hook for private scopes.
    return False


def visible_posts_for_agent(agent: Agent, posts: dict[str, Post], state: SimulationState | None = None) -> dict[str, Post]:
    """Social-aware visibility: prefer follow-neighbor and interaction-chain content."""

    if state is None:
        return {
            post_id: post
            for post_id, post in posts.items()
            if (post.visibility_scope or post.visibility) in {"public", "official_global"}
        }

    visible: dict[str, Post] = {}
    for post_id, post in posts.items():
        if not _is_scope_visible(agent, post, state):
            continue
        if post_id in state.suppressed_content and post.author_id != agent.agent_id:
            continue
        proximity = _social_proximity(agent, post, state)
        raw_target_ids = post.metadata.get("targeted_agent_ids", [])
        targeted_agent_ids = {str(item) for item in raw_target_ids} if isinstance(raw_target_ids, list) else set()
        targeted_for_agent = agent.agent_id in targeted_agent_ids
        if targeted_for_agent:
            proximity = max(proximity, 0.95)
        scope = post.visibility_scope or post.visibility
        pinned = post_id in state.official_pinned_content
        include = (
            scope == "official_global"
            or pinned
            or post.source_type in {"official", "fact_check"}
            or targeted_for_agent
            or proximity >= 0.18
            or post.heat >= 1.2
            or post.author_id == agent.agent_id
        )
        if not include:
            continue
        post.exposure_count += 1
        visible[post_id] = replace(
            post,
            metadata={
                **post.metadata,
                "social_proximity": round(proximity, 4),
                "visibility_scope": scope,
                "pinned": pinned,
                "targeted_for_agent": targeted_for_agent,
            },
        )
    return visible
