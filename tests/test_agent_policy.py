from vasociety.agents.policy import AgentPolicy
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post


def _agent() -> Agent:
    return Agent(
        agent_id="a1",
        name="A1",
        persona_type="silent_observer",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.3,
        conformity_level=0.4,
        skepticism_level=0.2,
        emotionality_level=0.2,
        authority_trust_level=0.6,
        topic_beliefs={"healthcare": 0.5},
        topic_stances={"healthcare": "neutral"},
    )


def test_policy_skip_when_seen_all() -> None:
    agent = _agent()
    agent.seen_content_ids.add("p1")
    posts = {"p1": Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official")}
    feed = [FeedItem("f1", "post", "p1", 1.0, "test")]
    decision = AgentPolicy(seed=7).decide(agent, feed, posts, step=1)
    assert decision.action == "skip"


def test_policy_updates_belief_state_delta() -> None:
    agent = _agent()
    posts = {"p1": Post("p1", "sys", 1, "fact", "healthcare", "corrective", "fact_check")}
    feed = [FeedItem("f1", "post", "p1", 1.0, "test")]
    decision = AgentPolicy(seed=1).decide(agent, feed, posts, step=1)
    assert "new_belief" in decision.state_delta or decision.state_delta == {}


def test_policy_deterministic_under_seed() -> None:
    agent_1 = _agent()
    agent_2 = _agent()
    posts = {"p1": Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official", heat=2.0)}
    feed = [FeedItem("f1", "post", "p1", 2.0, "test")]
    d1 = AgentPolicy(seed=99).decide(agent_1, feed, posts, step=1)
    d2 = AgentPolicy(seed=99).decide(agent_2, feed, posts, step=1)
    assert d1.action == d2.action
