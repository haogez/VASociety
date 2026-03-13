from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.analytics.explain import build_final_state_summary, generate_explanation_summary
from vasociety.analytics.trace_analyzer import metrics_trace_consistency, validate_decision_trace_schema
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def _run_state() -> SimulationState:
    interventions = [
        Intervention(
            intervention_id="iv1",
            step=1,
            type="inject_news",
            payload={"content": "x", "topic": "healthcare", "stance": "uncertain", "source_type": "official"},
        ),
        Intervention(
            intervention_id="iv2",
            step=2,
            type="inject_fact_check",
            payload={"content": "y", "topic": "healthcare", "stance": "corrective"},
        ),
    ]
    agents = AgentFactory(seed=17).create_population(8, ["healthcare", "economy"])
    state = SimulationState(agents=agents, interventions=interventions)
    engine = SimulationEngine(
        state=state,
        feed_ranker=FeedRanker(FeedWeights()),
        policy=AgentPolicy(seed=17, view_top_k=3),
        scheduler=InterventionScheduler(interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=17,
    )
    return engine.run(steps=5, snapshot_each_step=True)


def test_decision_trace_schema() -> None:
    state = _run_state()
    report = validate_decision_trace_schema(state.decision_trace)
    assert report["total_records"] > 0
    assert report["is_valid"] is True
    assert report["invalid_records"] == 0


def test_explanation_summary_generation() -> None:
    state = _run_state()
    summary = generate_explanation_summary(state)
    assert summary["run_id"] == state.run_id
    assert "topic_heat_over_time" in summary
    assert "stance_shift_summary" in summary
    assert "persona_participation_summary" in summary
    assert "top_diffusion_posts" in summary
    assert "metrics_trace_consistency" in summary


def test_metrics_trace_consistency_check() -> None:
    state = _run_state()
    report = metrics_trace_consistency(state)
    assert report["is_consistent"] is True
    assert report["checks"]


def test_final_state_summary_fields() -> None:
    state = _run_state()
    summary = build_final_state_summary(state)
    assert "per_agent_topic_stances_summary" in summary
    assert "key_counts" in summary
    assert "social_summary" in summary
