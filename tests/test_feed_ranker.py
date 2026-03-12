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
        trust_scores={"official": 0.9, "organic": 0.4},
    )


def test_feed_ranker_prefers_topic_and_official() -> None:
    agent = _agent()
    posts = {
        "p1": Post("p1", "u1", 1, "x", "healthcare", "supportive", "official", heat=1.0),
        "p2": Post("p2", "u2", 1, "y", "economy", "questioning", "organic", heat=1.0),
    }
    ranked = FeedRanker(FeedWeights(), max_items=2).rank(agent, posts, step=2)
    assert ranked[0].ref_id == "p1"


def test_seen_content_penalty_applies() -> None:
    agent = _agent()
    posts = {
        "p1": Post("p1", "u1", 1, "x", "healthcare", "supportive", "official", heat=1.0),
    }
    ranker = FeedRanker(FeedWeights(), max_items=1)
    score_before = ranker.rank(agent, posts, step=2)[0].score
    agent.seen_content_ids.add("p1")
    score_after = ranker.rank(agent, posts, step=2)[0].score
    assert score_after < score_before


def test_ranker_returns_breakdown_fields() -> None:
    item = FeedRanker(FeedWeights(), max_items=1).rank(
        _agent(), {"p1": Post("p1", "u", 1, "x", "healthcare", "supportive", "official", heat=1.0)}, step=2
    )[0]
    assert "heat_score" in item.breakdown
    assert "novelty_score" in item.breakdown
