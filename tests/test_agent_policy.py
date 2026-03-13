from copy import deepcopy

from vasociety.agents.policy import AgentPolicy
from vasociety.models.agent import Agent
from vasociety.models.content import FeedItem, Post


def _agent(
    persona_type: str = "silent_observer",
    expression: float = 0.3,
    conformity: float = 0.4,
    skepticism: float = 0.2,
    emotionality: float = 0.2,
) -> Agent:
    return Agent(
        agent_id=f"a_{persona_type}",
        name=f"A_{persona_type}",
        persona_type=persona_type,
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=expression,
        conformity_level=conformity,
        skepticism_level=skepticism,
        emotionality_level=emotionality,
        authority_trust_level=0.7,
        topic_beliefs={"healthcare": 0.6},
        topic_uncertainty={"healthcare": 0.5},
        topic_stances={"healthcare": "supportive"},
    )


def test_policy_skip_when_seen_all() -> None:
    agent = _agent()
    agent.seen_content_ids.add("p1")
    posts = {"p1": Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official")}
    feed = [FeedItem("f1", "post", "p1", 1.0, "test")]
    decision = AgentPolicy(seed=7).decide(agent, feed, posts, step=1)
    assert decision.action == "skip"
    assert decision.decision_reason == "all_seen"


def test_corrective_content_changes_belief() -> None:
    agent = _agent()
    previous_belief = agent.topic_beliefs["healthcare"]
    posts = {"p1": Post("p1", "sys", 1, "fact", "healthcare", "corrective", "fact_check", heat=1.8)}
    feed = [FeedItem("f1", "post", "p1", 1.2, "test")]
    decision = AgentPolicy(seed=11).decide(agent, feed, posts, step=1)
    assert agent.topic_beliefs["healthcare"] != previous_belief
    assert decision.state_delta["belief_delta"]["healthcare"] < 0
    assert "uncertainty_delta" in decision.state_delta


def test_different_persona_behaviors_on_same_content() -> None:
    expressive = _agent(persona_type="amplifier", expression=0.95, conformity=0.75, skepticism=0.1, emotionality=0.85)
    cautious = _agent(persona_type="skeptic", expression=0.1, conformity=0.15, skepticism=0.9, emotionality=0.1)

    post = Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official", heat=2.8, reposts=8, likes=6)
    posts_1 = {"p1": deepcopy(post)}
    posts_2 = {"p1": deepcopy(post)}
    feed_1 = [FeedItem("f1", "post", "p1", 2.0, "test")]
    feed_2 = [FeedItem("f1", "post", "p1", 2.0, "test")]

    d1 = AgentPolicy(seed=23).decide(expressive, feed_1, posts_1, step=1)
    d2 = AgentPolicy(seed=23).decide(cautious, feed_2, posts_2, step=1)

    assert d1.action != d2.action


def test_policy_deterministic_under_seed() -> None:
    agent_1 = _agent()
    agent_2 = _agent()
    posts_1 = {"p1": Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official", heat=2.0)}
    posts_2 = {"p1": Post("p1", "sys", 1, "news", "healthcare", "uncertain", "official", heat=2.0)}
    feed_1 = [FeedItem("f1", "post", "p1", 2.0, "test")]
    feed_2 = [FeedItem("f1", "post", "p1", 2.0, "test")]

    d1 = AgentPolicy(seed=99).decide(agent_1, feed_1, posts_1, step=1)
    d2 = AgentPolicy(seed=99).decide(agent_2, feed_2, posts_2, step=1)

    assert d1.action == d2.action
    assert d1.decision_reason == d2.decision_reason
    assert d1.state_delta["belief_delta"] == d2.state_delta["belief_delta"]
