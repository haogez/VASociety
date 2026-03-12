from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def test_engine_runs_and_collects_metrics() -> None:
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
        policy=AgentPolicy(seed=1),
        scheduler=InterventionScheduler(interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=1,
    )
    end = engine.run(steps=3)
    assert end.current_step == 3
    assert len(end.metrics_history) == 3
    assert len(end.posts) >= 1
