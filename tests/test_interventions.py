from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.environment.visibility import visible_posts_for_agent
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.models.agent import Agent
from vasociety.models.content import Post
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState


def _agent(agent_id: str = "a1") -> Agent:
    return Agent(
        agent_id=agent_id,
        name=agent_id,
        persona_type="rational_checker",
        interest_topics=["healthcare", "economy"],
        activity_profile=1.0,
        expression_level=0.5,
        conformity_level=0.5,
        skepticism_level=0.4,
        emotionality_level=0.3,
        authority_trust_level=0.7,
        topic_stances={"healthcare": "supportive", "economy": "neutral"},
        trust_scores={"official": 0.8, "organic": 0.5},
    )


def test_intervention_scheduler_by_step() -> None:
    interventions = [
        Intervention("a", 1, "inject_news", {}),
        Intervention("b", 3, "inject_fact_check", {}),
    ]
    scheduler = InterventionScheduler(interventions)
    assert [item.intervention_id for item in scheduler.get_for_step(1)] == ["a"]
    assert scheduler.get_for_step(2) == []
    assert [item.intervention_id for item in scheduler.get_for_step(3)] == ["b"]


def test_platform_boost_changes_feed_ranking() -> None:
    agent = _agent()
    state = SimulationState(current_step=1)
    state.posts["p1"] = Post("p1", "u1", 1, "x", "healthcare", "supportive", "organic", heat=1.0)
    state.posts["p2"] = Post("p2", "u2", 1, "x", "healthcare", "supportive", "organic", heat=2.2)

    ranker = FeedRanker(FeedWeights(), max_items=2, strategy="hotness_first")
    top_before = ranker.rank(agent, state.posts, step=1)[0].ref_id
    assert top_before == "p2"

    iv = Intervention("g1", 1, "platform_boost", {"post_id": "p1", "boost_add": 2.6})
    result = InterventionHandler().apply(iv, state)
    top_after = ranker.rank(agent, state.posts, step=1)[0].ref_id
    assert result["status"] == "applied"
    assert top_after == "p1"


def test_platform_suppress_reduces_visibility() -> None:
    agent = _agent()
    state = SimulationState(current_step=1, agents={agent.agent_id: agent})
    state.posts["p1"] = Post("p1", "u1", 1, "x", "healthcare", "supportive", "organic", heat=1.8)

    iv = Intervention("s1", 1, "platform_suppress", {"post_id": "p1"})
    result = InterventionHandler().apply(iv, state)
    visible = visible_posts_for_agent(agent, state.posts, state)
    assert result["status"] == "applied"
    assert "p1" in state.suppressed_content
    assert "p1" not in visible


def test_fact_check_injection_enters_content_pool() -> None:
    state = SimulationState(current_step=1)
    iv = Intervention(
        "fc1",
        1,
        "inject_fact_check",
        {"content": "纠偏信息", "topic": "healthcare", "stance": "corrective"},
    )
    result = InterventionHandler().apply(iv, state)
    created_post_id = result["created_post_ids"][0]

    env = PlatformEnvironment()
    env.refresh_content_pool(state.posts, current_step=1, state=state)

    assert state.posts[created_post_id].source_type == "fact_check"
    assert created_post_id in state.trending_pool
