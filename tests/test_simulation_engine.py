from pathlib import Path

from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.io.save import save_state
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def _build_engine(seed: int, interventions: list[Intervention]) -> SimulationEngine:
    agents = AgentFactory(seed=seed).create_population(6, ["healthcare", "economy"])
    state = SimulationState(agents=agents, interventions=list(interventions))
    return SimulationEngine(
        state=state,
        feed_ranker=FeedRanker(FeedWeights()),
        policy=AgentPolicy(seed=seed),
        scheduler=InterventionScheduler(interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=seed,
    )


def test_engine_runs_and_collects_metrics() -> None:
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        )
    ]
    engine = _build_engine(seed=1, interventions=interventions)
    end = engine.run(steps=3)
    assert end.current_step == 3
    assert len(end.metrics_history) == 3
    assert len(end.posts) >= 1


def test_engine_run_10_steps_successfully() -> None:
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        )
    ]
    end = _build_engine(seed=3, interventions=interventions).run(steps=10, snapshot_each_step=True)
    assert end.current_step == 10
    assert len(end.metrics_history) == 10
    assert len(end.snapshots) == 10


def test_interventions_affect_later_steps() -> None:
    interventions = [
        Intervention(
            intervention_id="news_1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        ),
        Intervention(
            intervention_id="sup_1",
            step=2,
            type="platform_suppress",
            payload={"topic": "healthcare"},
        ),
    ]
    end = _build_engine(seed=7, interventions=interventions).run(steps=4)
    news_event = next(
        item
        for item in end.event_log
        if item.get("event") == "intervention" and item.get("payload", {}).get("intervention_id") == "news_1"
    )
    created_post_id = str(news_event["payload"]["result"]["created_post_ids"][0])
    assert created_post_id in end.suppressed_content
    assert end.posts[created_post_id].metadata.get("suppressed") is True
    assert end.metrics_history[1].governance_action_count >= 1


def test_runtime_outputs_generated_correctly(tmp_path: Path) -> None:
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        )
    ]
    state = _build_engine(seed=11, interventions=interventions).run(steps=3, snapshot_each_step=True)
    save_state(state, tmp_path, write_decision_trace=True)
    assert (tmp_path / "final_state.json").exists()
    assert (tmp_path / "world_state.json").exists()
    assert (tmp_path / "run_artifacts.json").exists()
    assert (tmp_path / "metrics_history.json").exists()
    assert (tmp_path / "event_log.jsonl").exists()
    assert (tmp_path / "decision_trace.jsonl").exists()


def test_fixed_seed_runtime_reproducible() -> None:
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        )
    ]
    state_a = _build_engine(seed=13, interventions=interventions).run(steps=5)
    state_b = _build_engine(seed=13, interventions=interventions).run(steps=5)
    assert [m.active_agents for m in state_a.metrics_history] == [m.active_agents for m in state_b.metrics_history]
    assert [m.discussion_heat for m in state_a.metrics_history] == [m.discussion_heat for m in state_b.metrics_history]


def test_engine_step_mode_supports_dynamic_intervention() -> None:
    engine = _build_engine(seed=19, interventions=[])
    engine.step(snapshot_each_step=False)
    assert engine.state.current_step == 1

    intervention = Intervention(
        intervention_id="manual_001",
        step=2,
        type="inject_news",
        payload={"content": "dynamic", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
    )
    engine.schedule_intervention(intervention)
    engine.step(snapshot_each_step=False)

    assert engine.state.current_step == 2
    assert any(post.metadata.get("intervention_id") == "manual_001" for post in engine.state.posts.values())
    assert any(
        item.get("event") == "intervention" and item.get("payload", {}).get("intervention_id") == "manual_001"
        for item in engine.state.event_log
    )
