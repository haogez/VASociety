from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.models.agent import Agent
from vasociety.models.content import Post


def test_feed_ranker_prefers_topic_and_official() -> None:
    agent = Agent(
        agent_id="a1",
        name="A1",
        persona_type="rational_checker",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.5,
        conformity_level=0.5,
        skepticism_level=0.5,
        emotionality_level=0.5,
        authority_trust_level=0.5,
    )
    posts = {
        "p1": Post(
            post_id="p1",
            author_id="u1",
            created_at_step=1,
            content="x",
            topic="healthcare",
            stance="supportive",
            source_type="official",
            heat=1.0,
        ),
        "p2": Post(
            post_id="p2",
            author_id="u2",
            created_at_step=1,
            content="y",
            topic="economy",
            stance="questioning",
            source_type="organic",
            heat=1.0,
        ),
    }
    ranker = FeedRanker(FeedWeights(), max_items=2)
    ranked = ranker.rank(agent, posts, step=2)
    assert ranked[0].ref_id == "p1"
