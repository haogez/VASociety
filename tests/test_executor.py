from vasociety.agents.policy import Decision
from vasociety.models.agent import Agent
from vasociety.models.content import Post
from vasociety.models.state import SimulationState
from vasociety.simulation.executor import ActionExecutor


def _state_and_agent() -> tuple[SimulationState, Agent]:
    agent = Agent(
        agent_id="a1",
        name="A1",
        persona_type="expressive_speaker",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.9,
        conformity_level=0.5,
        skepticism_level=0.3,
        emotionality_level=0.5,
        authority_trust_level=0.5,
    )
    state = SimulationState(current_step=1, agents={"a1": agent})
    state.posts["p1"] = Post("p1", "sys", 1, "n", "healthcare", "uncertain", "official")
    return state, agent


def test_comment_updates_count_and_comment_store() -> None:
    state, agent = _state_and_agent()
    ActionExecutor().execute(state, agent, Decision(action="comment", target_post_id="p1", content="c", stance="neutral"))
    assert state.posts["p1"].comments_count == 1
    assert len(state.comments) == 1


def test_repost_parent_linkage() -> None:
    state, agent = _state_and_agent()
    ActionExecutor().execute(state, agent, Decision(action="repost", target_post_id="p1"))
    repost = [p for p in state.posts.values() if p.parent_post_id == "p1"]
    assert len(repost) == 1


def test_create_post_generates_new_post() -> None:
    state, agent = _state_and_agent()
    ActionExecutor().execute(state, agent, Decision(action="create_post", content="hello", stance="questioning"))
    assert len(state.posts) == 2
