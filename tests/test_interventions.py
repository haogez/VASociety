from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState


def test_intervention_scheduler_by_step() -> None:
    interventions = [
        Intervention("a", 1, "inject_news", {}),
        Intervention("b", 2, "inject_fact_check", {}),
    ]
    scheduler = InterventionScheduler(interventions)
    assert len(scheduler.get_for_step(1)) == 1
    assert scheduler.get_for_step(3) == []


def test_handler_inject_news_creates_post() -> None:
    state = SimulationState(current_step=1)
    iv = Intervention("n1", 1, "inject_news", {"content": "c", "topic": "t", "stance": "uncertain"})
    InterventionHandler().apply(iv, state)
    assert len(state.posts) == 1


def test_handler_reserved_type_returns_reserved() -> None:
    state = SimulationState(current_step=1)
    iv = Intervention("r1", 1, "platform_boost", {})
    result = InterventionHandler().apply(iv, state)
    assert result["status"] == "reserved"
