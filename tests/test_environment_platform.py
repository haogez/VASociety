from vasociety.agents.factory import AgentFactory
from vasociety.environment.platform import PlatformEnvironment
from vasociety.environment.visibility import visible_posts_for_agent
from vasociety.models.content import Post
from vasociety.models.state import SimulationState


def test_heat_decay_with_freshness() -> None:
    env = PlatformEnvironment(heat_decay=0.9, freshness_penalty=0.04)
    post = Post(
        post_id="p1",
        author_id="a1",
        created_at_step=1,
        content="x",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        heat=2.0,
        last_active_step=1,
    )
    env.decay_heat({"p1": post}, current_step=6)
    assert post.heat < 2.0
    assert post.heat >= env.min_heat


def test_exposure_count_updates_on_visibility() -> None:
    agents = AgentFactory(seed=3).create_population(2, ["healthcare"])
    state = SimulationState(agents=agents)
    state.followees.update({"agent_000": ["agent_001"]})
    state.followers.update({"agent_001": ["agent_000"]})
    state.trust_edges.update({"agent_000": {"agent_001": 0.8}})
    state.affinity_edges.update({"agent_000": {"agent_001": 0.8}})

    post = Post(
        post_id="p1",
        author_id="agent_001",
        created_at_step=1,
        content="x",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        heat=1.3,
    )
    before = post.exposure_count
    visible = visible_posts_for_agent(agents["agent_000"], {"p1": post}, state)
    assert "p1" in visible
    assert post.exposure_count == before + 1


def test_visibility_followers_only_filtering() -> None:
    agents = AgentFactory(seed=4).create_population(3, ["healthcare"])
    state = SimulationState(agents=agents)
    state.followees.update({"agent_001": ["agent_000"], "agent_002": []})
    state.followers.update({"agent_000": ["agent_001"], "agent_001": [], "agent_002": []})

    post = Post(
        post_id="p_followers",
        author_id="agent_000",
        created_at_step=1,
        content="x",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        visibility_scope="followers_only",
        visibility="followers_only",
        heat=2.0,
    )

    visible_follower = visible_posts_for_agent(agents["agent_001"], {"p_followers": post}, state)
    visible_stranger = visible_posts_for_agent(agents["agent_002"], {"p_followers": post}, state)
    assert "p_followers" in visible_follower
    assert "p_followers" not in visible_stranger


def test_official_global_visible_to_all() -> None:
    agents = AgentFactory(seed=5).create_population(2, ["healthcare"])
    state = SimulationState(agents=agents)
    post = Post(
        post_id="p_global",
        author_id="system_news",
        created_at_step=1,
        content="official",
        topic="healthcare",
        stance="corrective",
        source_type="official",
        visibility_scope="official_global",
        visibility="official_global",
        heat=0.2,
    )
    visible = visible_posts_for_agent(agents["agent_000"], {"p_global": post}, state)
    assert "p_global" in visible
