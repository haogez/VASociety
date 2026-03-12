"""CLI entrypoint for running VASociety simulations."""

from __future__ import annotations

import argparse
from pathlib import Path

from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.config import load_config
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.io.load import parse_interventions
from vasociety.io.save import save_state
from vasociety.logger import setup_logger
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.scheduler import InterventionScheduler


def run(config: Path) -> None:
    """Run one simulation using a configuration file."""

    cfg = load_config(config)
    logger = setup_logger(cfg.log_level, cfg.output_dir)

    factory = AgentFactory(seed=cfg.seed)
    agents = factory.create_population(
        count=int(cfg.agent_population.get("count", 20)),
        topics=list(cfg.agent_population.get("topics", ["general"])),
    )

    state = SimulationState(agents=agents, interventions=parse_interventions(cfg.interventions))
    weights = FeedWeights(**cfg.feed.get("weights", {}))
    feed_ranker = FeedRanker(weights=weights, max_items=int(cfg.feed.get("max_items", 8)))

    engine = SimulationEngine(
        state=state,
        feed_ranker=feed_ranker,
        policy=AgentPolicy(seed=cfg.seed),
        scheduler=InterventionScheduler(state.interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        seed=cfg.seed,
    )

    final_state = engine.run(steps=cfg.steps, snapshot_each_step=cfg.snapshot_each_step)
    save_state(final_state, cfg.output_dir)

    latest = final_state.metrics_history[-1]
    heat_by_step = [m.discussion_heat for m in final_state.metrics_history]
    active_by_step = [m.active_agents for m in final_state.metrics_history]
    print("\n=== VASociety Demo Summary ===")
    print(f"Total posts: {latest.total_posts}")
    print(f"Total comments: {latest.total_comments}")
    print(f"Total reposts: {latest.total_reposts}")
    print(f"Active agents by step: {active_by_step}")
    print(f"Discussion heat by step: {heat_by_step}")
    print(f"Outputs saved to: {cfg.output_dir}")
    logger.info("Simulation completed with %s posts and %s comments", latest.total_posts, latest.total_comments)


def main() -> None:
    """Parse CLI arguments and execute a simulation run."""

    parser = argparse.ArgumentParser(description="VASociety phase-1 simulation CLI")
    parser.add_argument("run", nargs="?", default="run")
    parser.add_argument("--config", "-c", type=Path, default=Path("configs/demo.yaml"))
    args = parser.parse_args()
    run(config=args.config)


if __name__ == "__main__":
    main()
