import json
from pathlib import Path

from vasociety.agents.factory import AgentFactory
from vasociety.io.load import load_runtime_state
from vasociety.models.content import Comment, Post
from vasociety.models.metrics import MetricsSnapshot
from vasociety.models.state import RunArtifacts, WorldState


def test_world_state_serialization_roundtrip() -> None:
    agents = AgentFactory(seed=3).create_population(2, ["healthcare"])
    world = WorldState(
        current_step=2,
        agents=agents,
        followees={"agent_000": ["agent_001"]},
        followers={"agent_001": ["agent_000"]},
        trust_edges={"agent_000": {"agent_001": 0.7}},
        community_labels={"agent_000": "c1", "agent_001": "c1"},
    )
    world.posts["post_00001"] = Post(
        post_id="post_00001",
        author_id="agent_000",
        created_at_step=1,
        content="x",
        topic="healthcare",
        stance="neutral",
        source_type="organic",
        origin_post_id="post_00001",
        diffusion_path=["post_00001"],
        exposure_count=2,
    )
    world.comments["comment_00001"] = Comment(
        comment_id="comment_00001",
        post_id="post_00001",
        author_id="agent_001",
        created_at_step=2,
        content="ok",
        stance="neutral",
    )

    payload = world.to_dict()
    restored = WorldState.from_dict(payload)
    assert restored.current_step == 2
    assert restored.posts["post_00001"].origin_post_id == "post_00001"
    assert restored.posts["post_00001"].diffusion_path == ["post_00001"]
    assert restored.posts["post_00001"].exposure_count == 2
    assert restored.follow_graph["agent_000"] == ["agent_001"]
    assert restored.trust_graph["agent_000"]["agent_001"] == 0.7


def test_run_artifacts_serialization_roundtrip() -> None:
    artifacts = RunArtifacts(
        metrics_history=[
            MetricsSnapshot(
                step=1,
                total_posts=1,
                total_comments=0,
                total_likes=0,
                total_reposts=0,
                discussion_heat=1.0,
                active_agents=1,
                stance_distribution={"neutral": 1.0},
            )
        ],
        event_log=[{"step": 1, "event": "x"}],
        decision_trace=[{"step": 1, "agent_id": "agent_000"}],
        snapshots=[{"step": 1, "post_count": 1}],
    )
    restored = RunArtifacts.from_dict(artifacts.to_dict())
    assert restored.metrics_history[0].step == 1
    assert restored.event_log[0]["event"] == "x"
    assert restored.decision_trace[0]["agent_id"] == "agent_000"
    assert restored.snapshots[0]["post_count"] == 1


def test_backward_compat_output_loading(tmp_path: Path) -> None:
    (tmp_path / "final_state.json").write_text(
        json.dumps(
            {
                "current_step": 1,
                "posts": [
                    {
                        "post_id": "post_00001",
                        "author_id": "a1",
                        "created_at_step": 1,
                        "content": "x",
                        "topic": "healthcare",
                        "stance": "neutral",
                        "source_type": "organic",
                        "parent_post_id": None,
                        "visibility": "public",
                        "heat": 1.0,
                        "likes": 0,
                        "reposts": 0,
                        "comments_count": 0,
                        "metadata": {},
                    }
                ],
                "comments": [
                    {
                        "comment_id": "comment_00001",
                        "post_id": "post_00001",
                        "author_id": "a2",
                        "created_at_step": 1,
                        "content": "ok",
                        "stance": "neutral",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "metrics_history.json").write_text(
        json.dumps(
            [
                {
                    "step": 1,
                    "total_posts": 1,
                    "total_comments": 1,
                    "total_likes": 0,
                    "total_reposts": 0,
                    "discussion_heat": 1.0,
                    "active_agents": 1,
                    "stance_distribution": {"neutral": 1.0},
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "event_log.jsonl").write_text('{"step":1,"event":"metrics"}\n', encoding="utf-8")
    (tmp_path / "decision_trace.jsonl").write_text('{"step":1,"agent_id":"agent_000"}\n', encoding="utf-8")

    state = load_runtime_state(Path(tmp_path))
    assert state.current_step == 1
    assert "post_00001" in state.posts
    assert "comment_00001" in state.comments
    assert len(state.metrics_history) == 1
    assert state.event_log[0]["event"] == "metrics"
