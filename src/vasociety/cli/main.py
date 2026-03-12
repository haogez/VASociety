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
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.io.load import parse_interventions
from vasociety.io.save import save_state
from vasociety.logger import setup_logger
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def run(config: Path) -> None:
    cfg = load_config(config)
    logger = setup_logger(cfg.log_level, cfg.output.output_dir)

    agents = AgentFactory(seed=cfg.seed).create_population(
        count=cfg.agent_population.count,
        topics=cfg.agent_population.topics,
    )

    state = SimulationState(agents=agents, interventions=parse_interventions(cfg.interventions))
    weights = FeedWeights(
        heat=cfg.feed.weights.heat,
        freshness=cfg.feed.weights.freshness,
        topic_match=cfg.feed.weights.topic_match,
        stance_affinity=cfg.feed.weights.stance_affinity,
        official_boost=cfg.feed.weights.official_boost,
        source_trust=cfg.feed.weights.source_trust,
        social_proximity=cfg.feed.weights.social_proximity,
        novelty=cfg.feed.weights.novelty,
    )

    engine = SimulationEngine(
        state=state,
        feed_ranker=FeedRanker(weights=weights, max_items=cfg.feed.max_items),
        policy=AgentPolicy(seed=cfg.seed, view_top_k=cfg.feed.view_top_k),
        scheduler=InterventionScheduler(state.interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=cfg.seed,
    )

    final_state = engine.run(steps=cfg.steps, snapshot_each_step=cfg.output.snapshot_each_step)
    save_state(final_state, cfg.output.output_dir, write_decision_trace=cfg.output.write_decision_trace)

    latest = final_state.metrics_history[-1]
    print("\n=== VASociety Demo Summary ===")
    print(f"Total posts: {latest.total_posts}")
    print(f"Total comments: {latest.total_comments}")
    print(f"Total reposts: {latest.total_reposts}")
    print(f"Active agents by step: {[m.active_agents for m in final_state.metrics_history]}")
    print(f"Discussion heat by step: {[m.discussion_heat for m in final_state.metrics_history]}")
    print(f"Stance shifts: {latest.stance_shift_count}")
    print(f"Outputs saved to: {cfg.output.output_dir}")
    logger.info("Simulation completed with %s posts and %s comments", latest.total_posts, latest.total_comments)


def main() -> None:
    parser = argparse.ArgumentParser(description="VASociety simulation CLI")
    parser.add_argument("run", nargs="?", default="run")
    parser.add_argument("--config", "-c", type=Path, default=Path("configs/demo.yaml"))
    args = parser.parse_args()
    run(config=args.config)


if __name__ == "__main__":
    main()
