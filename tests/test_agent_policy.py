from vasociety.agents.policy import AgentPolicy
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post


def test_policy_skip_when_seen() -> None:
    agent = Agent(
        agent_id="a1",
        name="A1",
        persona_type="silent_observer",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.1,
        conformity_level=0.4,
        skepticism_level=0.4,
        emotionality_level=0.2,
        authority_trust_level=0.5,
    )
    agent.seen_content_ids.add("p1")
    posts = {
        "p1": Post(
            post_id="p1",
            author_id="sys",
            created_at_step=1,
            content="news",
            topic="healthcare",
            stance="uncertain",
            source_type="official",
        )
    }
    feed = [FeedItem(item_id="f1", item_type="post", ref_id="p1", score=1.0, reason="test")]
    decision = AgentPolicy(seed=7).decide(agent, feed, posts)
    assert decision.action == "skip"
