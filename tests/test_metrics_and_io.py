from pathlib import Path

from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.io.save import save_state
from vasociety.metrics.collector import MetricsCollector
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def _run_small() -> SimulationState:
    agents = AgentFactory(seed=1).create_population(6, ["healthcare", "economy"])
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        )
    ]
    state = SimulationState(agents=agents, interventions=interventions)
    engine = SimulationEngine(
        state=state,
        feed_ranker=FeedRanker(FeedWeights()),
        policy=AgentPolicy(seed=1, view_top_k=3),
        scheduler=InterventionScheduler(interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=1,
    )
    return engine.run(steps=3, snapshot_each_step=True)


def test_metrics_include_extended_fields() -> None:
    state = _run_small()
    metrics = MetricsCollector.collect(state, active_agents=1)
    assert isinstance(metrics.persona_participation, dict)
    assert isinstance(metrics.per_step_topic_heat, dict)


def test_output_file_generation(tmp_path: Path) -> None:
    state = _run_small()
    save_state(state, tmp_path, write_decision_trace=True)
    assert (tmp_path / "final_state.json").exists()
    assert (tmp_path / "world_state.json").exists()
    assert (tmp_path / "run_artifacts.json").exists()
    assert (tmp_path / "metrics_history.json").exists()
    assert (tmp_path / "event_log.jsonl").exists()
    assert (tmp_path / "perception_log.jsonl").exists()
    assert (tmp_path / "decision_log.jsonl").exists()
    assert (tmp_path / "execution_log.jsonl").exists()
    assert (tmp_path / "intervention_log.jsonl").exists()
    assert (tmp_path / "metrics_log.jsonl").exists()
    assert (tmp_path / "decision_trace.jsonl").exists()
    assert (tmp_path / "trace_analysis.json").exists()
    assert (tmp_path / "explanation_summary.json").exists()


def test_backward_compatible_demo_config_runs() -> None:
    state = _run_small()
    assert state.current_step == 3
    assert len(state.metrics_history) == 3
