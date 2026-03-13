from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.models.agent import Agent
from vasociety.models.content import Post


def _agent() -> Agent:
    return Agent(
        agent_id="a1",
        name="A1",
        persona_type="rational_checker",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.5,
        conformity_level=0.5,
        skepticism_level=0.5,
        emotionality_level=0.5,
        authority_trust_level=0.7,
        topic_stances={"healthcare": "supportive"},
        trust_scores={"official": 0.9, "organic": 0.4, "u_social": 0.9, "u_cold": 0.1},
    )


def test_official_boost_component_effective() -> None:
    agent = _agent()
    posts = {
        "official_post": Post("official_post", "u_official", 1, "x", "healthcare", "supportive", "official", heat=1.0),
        "organic_post": Post("organic_post", "u_organic", 1, "x", "healthcare", "supportive", "organic", heat=1.0),
    }
    ranker = FeedRanker(FeedWeights(official_boost=2.0), max_items=2, strategy="balanced")
    ranked = ranker.rank(agent, posts, step=2)
    assert ranked[0].ref_id == "official_post"
    assert ranked[0].breakdown["official_boost_score"] > ranked[1].breakdown["official_boost_score"]


def test_social_proximity_component_effective() -> None:
    agent = _agent()
    posts = {
        "p_social": Post(
            "p_social",
            "u_social",
            1,
            "x",
            "economy",
            "neutral",
            "organic",
            heat=1.0,
            metadata={"social_proximity": 1.0},
        ),
        "p_cold": Post(
            "p_cold",
            "u_cold",
            1,
            "x",
            "economy",
            "neutral",
            "organic",
            heat=1.0,
            metadata={"social_proximity": 0.0},
        ),
    }
    ranker = FeedRanker(FeedWeights(social_proximity=2.5), max_items=2, strategy="social_first")
    ranked = ranker.rank(agent, posts, step=2)
    assert ranked[0].ref_id == "p_social"
    assert ranked[0].breakdown["social_proximity_score"] > ranked[1].breakdown["social_proximity_score"]


def test_seen_content_penalty_applies() -> None:
    agent = _agent()
    posts = {
        "p1": Post("p1", "u1", 1, "x", "healthcare", "supportive", "official", heat=1.0),
    }
    ranker = FeedRanker(FeedWeights(), max_items=1, strategy="balanced")
    score_before = ranker.rank(agent, posts, step=2)[0].score
    agent.seen_content_ids.add("p1")
    score_after = ranker.rank(agent, posts, step=2)[0].score
    assert score_after < score_before


def test_different_strategy_changes_ordering() -> None:
    agent = _agent()
    posts = {
        "p_hot": Post("p_hot", "u_hot", 1, "x", "economy", "neutral", "organic", heat=3.5),
        "p_interest": Post("p_interest", "u_interest", 1, "x", "healthcare", "supportive", "organic", heat=1.2),
        "p_social": Post(
            "p_social",
            "u_social",
            1,
            "x",
            "economy",
            "neutral",
            "organic",
            heat=1.2,
            metadata={"social_proximity": 1.0},
        ),
    }

    ranker_hot = FeedRanker(FeedWeights(), max_items=3, strategy="hotness_first")
    ranker_interest = FeedRanker(FeedWeights(), max_items=3, strategy="interest_first")
    ranker_social = FeedRanker(FeedWeights(), max_items=3, strategy="social_first")

    hot_top = ranker_hot.rank(agent, posts, step=2)[0].ref_id
    interest_top = ranker_interest.rank(agent, posts, step=2)[0].ref_id
    social_top = ranker_social.rank(agent, posts, step=2)[0].ref_id

    assert hot_top == "p_hot"
    assert interest_top == "p_interest"
    assert social_top == "p_social"
    assert len({hot_top, interest_top, social_top}) == 3


def test_ranker_returns_reason_and_breakdown() -> None:
    item = FeedRanker(FeedWeights(), max_items=1, strategy="balanced").rank(
        _agent(),
        {"p1": Post("p1", "u", 1, "x", "healthcare", "supportive", "official", heat=1.0)},
        step=2,
    )[0]
    assert "strategy=balanced" in item.reason
    assert "heat_score" in item.breakdown
    assert "novelty_score" in item.breakdown
