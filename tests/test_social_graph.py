from vasociety.agents.factory import AgentFactory
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.visibility import visible_posts_for_agent
from vasociety.models.content import Post
from vasociety.models.state import SimulationState
from vasociety.social.graph import initialize_social_graph
from vasociety.social.trust import update_trust_by_interaction


def test_follow_graph_initialization() -> None:
    agents = AgentFactory(seed=12).create_population(8, ["healthcare", "economy", "education"])
    state = SimulationState(agents=agents)
    initialize_social_graph(state, seed=12, min_followees=1, max_followees=3)

    assert len(state.followees) == len(agents)
    assert len(state.followers) == len(agents)
    assert len(state.community_labels) == len(agents)
    for agent_id, neighbors in state.followees.items():
        assert len(neighbors) >= 1
        assert agent_id not in neighbors


def test_trust_update_increases_and_decreases() -> None:
    agents = AgentFactory(seed=2).create_population(2, ["healthcare"])
    state = SimulationState(agents=agents)
    state.trust_edges.update({"agent_000": {"agent_001": 0.5}, "agent_001": {"agent_000": 0.5}})

    boosted = update_trust_by_interaction(
        state=state,
        actor_id="agent_000",
        target_author_id="agent_001",
        action="comment",
        stance_conflict=0.0,
        interaction_count=3,
    )
    lowered = update_trust_by_interaction(
        state=state,
        actor_id="agent_000",
        target_author_id="agent_001",
        action="comment",
        stance_conflict=1.0,
        interaction_count=1,
    )

    assert boosted["new"] > boosted["prev"]
    assert lowered["new"] < boosted["new"]


def test_social_neighbor_content_ranked_higher() -> None:
    agents = AgentFactory(seed=9).create_population(3, ["healthcare", "economy"])
    state = SimulationState(agents=agents)
    state.followees.update({"agent_000": ["agent_001"], "agent_001": [], "agent_002": []})
    state.followers.update({"agent_001": ["agent_000"], "agent_000": [], "agent_002": []})
    state.trust_edges.update({"agent_000": {"agent_001": 0.9, "agent_002": 0.1}})
    state.affinity_edges.update({"agent_000": {"agent_001": 0.8, "agent_002": 0.2}})

    post_neighbor = Post(
        post_id="p_neighbor",
        author_id="agent_001",
        created_at_step=1,
        content="x",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        heat=1.6,
    )
    post_stranger = Post(
        post_id="p_stranger",
        author_id="agent_002",
        created_at_step=1,
        content="y",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        heat=1.6,
    )
    posts = {post_neighbor.post_id: post_neighbor, post_stranger.post_id: post_stranger}

    visible = visible_posts_for_agent(agents["agent_000"], posts, state)
    assert "p_neighbor" in visible
    assert "p_stranger" in visible
    assert visible["p_neighbor"].metadata["social_proximity"] > visible["p_stranger"].metadata["social_proximity"]

    ranker = FeedRanker(
        FeedWeights(
            heat=1.0,
            freshness=0.0,
            topic_match=0.0,
            stance_affinity=0.0,
            official_boost=0.0,
            source_trust=0.0,
            social_proximity=3.0,
            novelty=0.0,
        )
    )
    ranked = ranker.rank(agent=agents["agent_000"], posts=visible, step=2)
    assert ranked[0].ref_id == "p_neighbor"
