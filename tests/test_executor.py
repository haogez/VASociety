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
        topic_stances={"healthcare": "supportive"},
    )
    another = Agent(
        agent_id="a2",
        name="A2",
        persona_type="rational_checker",
        interest_topics=["healthcare"],
        activity_profile=1.0,
        expression_level=0.3,
        conformity_level=0.5,
        skepticism_level=0.6,
        emotionality_level=0.3,
        authority_trust_level=0.7,
        topic_stances={"healthcare": "neutral"},
    )
    state = SimulationState(current_step=1, agents={"a1": agent, "a2": another})
    state.posts["p1"] = Post("p1", "sys", 1, "n", "healthcare", "uncertain", "official")
    return state, agent


def test_like_updates_likes() -> None:
    state, agent = _state_and_agent()
    result = ActionExecutor().execute(state, agent, Decision(action="like", target_post_id="p1"))
    assert result["status"] == "executed"
    assert state.posts["p1"].likes == 1
    assert state.posts["p1"].heat > 1.0
    assert state.posts["p1"].exposure_count == 1
    assert len(agent.action_history) == 1
    assert state.event_log[-1]["event"] == "execution_log"
    assert state.decision_trace[-1]["execution"]["status"] == "executed"


def test_comment_updates_count_and_comment_store() -> None:
    state, agent = _state_and_agent()
    result = ActionExecutor().execute(
        state,
        agent,
        Decision(action="comment", target_post_id="p1", content="c", stance="neutral"),
    )
    assert result["status"] == "executed"
    assert str(result["created_comment_id"]).startswith("comment_")
    assert state.posts["p1"].comments_count == 1
    assert len(state.comments) == 1


def test_repost_parent_linkage() -> None:
    state, agent = _state_and_agent()
    result = ActionExecutor().execute(state, agent, Decision(action="repost", target_post_id="p1"))
    assert result["status"] == "executed"
    assert state.posts["p1"].reposts == 1
    created_post_id = str(result["created_post_id"])
    repost = state.posts[created_post_id]
    assert repost.parent_post_id == "p1"
    assert repost.origin_post_id == "p1"
    assert repost.diffusion_path[-1] == created_post_id


def test_create_post_generates_new_post() -> None:
    state, agent = _state_and_agent()
    result = ActionExecutor().execute(state, agent, Decision(action="create_post", stance="questioning"))
    assert result["status"] == "executed"
    assert len(state.posts) == 2
    created_post_id = str(result["created_post_id"])
    assert state.posts[created_post_id].origin_post_id == created_post_id
    assert state.posts[created_post_id].content


def test_invalid_action_rejected() -> None:
    state, agent = _state_and_agent()
    result = ActionExecutor().execute(state, agent, Decision(action="invalid_action", target_post_id="p1"))
    assert result["status"] == "rejected"
    assert str(result["rejection_reason"]).startswith("unsupported_action")
    assert state.posts["p1"].likes == 0
    assert len(state.comments) == 0
    assert len(agent.action_history) == 0
