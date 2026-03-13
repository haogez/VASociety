"""CLI entrypoint for running VASociety simulations."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vasociety.analytics.explain import generate_explanation_summary
from vasociety.analytics.trace_analyzer import metrics_trace_consistency, validate_decision_trace_schema
from vasociety.agents.factory import AgentFactory
from vasociety.agents.policy import AgentPolicy
from vasociety.config import INTERVENTION_TYPES, load_config
from vasociety.environment.feed_ranker import FeedRanker, FeedWeights
from vasociety.environment.platform import PlatformEnvironment
from vasociety.interventions.handlers import InterventionHandler
from vasociety.interventions.scheduler import InterventionScheduler
from vasociety.io.load import load_runtime_state, parse_interventions
from vasociety.io.save import save_state
from vasociety.logger import setup_logger
from vasociety.models.intervention import Intervention
from vasociety.models.state import SimulationState
from vasociety.simulation.engine import SimulationEngine
from vasociety.simulation.executor import ActionExecutor
from vasociety.simulation.recorder import SnapshotRecorder, StructuredEventLogger


def _build_engine(cfg: Any) -> tuple[SimulationEngine, SimulationState]:
    agents = AgentFactory(seed=cfg.simulation.random_seed).create_population(
        count=cfg.initial_population.count,
        topics=cfg.initial_population.topics,
    )

    normalized_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in cfg.scenario_name)
    state = SimulationState(
        run_id=f"run_{normalized_name}_seed_{cfg.simulation.random_seed}",
        scenario_name=cfg.scenario_name,
        agents=agents,
        interventions=parse_interventions(cfg.interventions),
    )
    weights = FeedWeights(
        heat=cfg.platform_rules.feed.weights.heat,
        freshness=cfg.platform_rules.feed.weights.freshness,
        topic_match=cfg.platform_rules.feed.weights.topic_match,
        stance_affinity=cfg.platform_rules.feed.weights.stance_affinity,
        official_boost=cfg.platform_rules.feed.weights.official_boost,
        source_trust=cfg.platform_rules.feed.weights.source_trust,
        social_proximity=cfg.platform_rules.feed.weights.social_proximity,
        novelty=cfg.platform_rules.feed.weights.novelty,
    )

    engine = SimulationEngine(
        state=state,
        feed_ranker=FeedRanker(
            weights=weights,
            max_items=cfg.platform_rules.feed.max_items,
            strategy=cfg.platform_rules.feed.ranking_strategy,
        ),
        policy=AgentPolicy(seed=cfg.simulation.random_seed, view_top_k=cfg.platform_rules.feed.view_top_k),
        scheduler=InterventionScheduler(state.interventions),
        env=PlatformEnvironment(),
        intervention_handler=InterventionHandler(),
        action_executor=ActionExecutor(),
        snapshot_recorder=SnapshotRecorder(),
        structured_logger=StructuredEventLogger(),
        seed=cfg.simulation.random_seed,
    )
    return engine, state


def run_single_scenario(
    config: Path,
    output_dir: Path | None = None,
    seed: int | None = None,
    steps: int | None = None,
    snapshot_each_step: bool | None = None,
    write_decision_trace: bool | None = None,
    emit_summary: bool = True,
) -> SimulationState:
    cfg = load_config(config)
    if output_dir is not None:
        cfg.output.output_dir = output_dir
    if seed is not None:
        cfg.simulation.random_seed = int(seed)
    if steps is not None:
        cfg.simulation.simulation_steps = max(1, int(steps))
    if snapshot_each_step is not None:
        cfg.output.snapshot_each_step = bool(snapshot_each_step)
    if write_decision_trace is not None:
        cfg.output.write_decision_trace = bool(write_decision_trace)

    logger = setup_logger(cfg.log_level, cfg.output.output_dir)
    engine, _ = _build_engine(cfg)

    final_state = engine.run(steps=cfg.simulation.simulation_steps, snapshot_each_step=cfg.output.snapshot_each_step)
    save_state(final_state, cfg.output.output_dir, write_decision_trace=cfg.output.write_decision_trace)

    latest = final_state.metrics_history[-1]
    if emit_summary:
        print("\n=== VASociety Run Summary ===")
        print(f"Run ID: {final_state.run_id}")
        print(f"Scenario: {cfg.scenario_name}")
        print(f"Total posts: {latest.total_posts}")
        print(f"Total comments: {latest.total_comments}")
        print(f"Total reposts: {latest.total_reposts}")
        print(f"Active agents by step: {[m.active_agents for m in final_state.metrics_history]}")
        print(f"Discussion heat by step: {[m.discussion_heat for m in final_state.metrics_history]}")
        print(f"Stance shifts: {latest.stance_shift_count}")
        print(f"Outputs saved to: {cfg.output.output_dir}")
    logger.info("Simulation completed with %s posts and %s comments", latest.total_posts, latest.total_comments)
    return final_state


def run(config: Path) -> SimulationState:
    return run_single_scenario(config=config)


def _pending_interventions(state: SimulationState) -> list[Intervention]:
    return sorted(
        [item for item in state.interventions if int(item.step) > state.current_step],
        key=lambda item: (int(item.step), str(item.intervention_id)),
    )


def _print_step_summary(state: SimulationState) -> None:
    latest = state.metrics_history[-1] if state.metrics_history else None
    pending_count = len(_pending_interventions(state))
    if latest is None:
        print(f"[step={state.current_step}] posts={len(state.posts)} comments={len(state.comments)} pending={pending_count}")
        return
    print(
        "[step={step}] posts={posts} comments={comments} active={active} heat={heat:.3f} pending={pending}".format(
            step=state.current_step,
            posts=latest.total_posts,
            comments=latest.total_comments,
            active=latest.active_agents,
            heat=float(latest.discussion_heat),
            pending=pending_count,
        )
    )


def _print_runtime_status(state: SimulationState, planned_steps: int) -> None:
    print(f"Current step: {state.current_step} (scenario plan: {planned_steps})")
    _print_step_summary(state)
    pending = _pending_interventions(state)
    if not pending:
        print("Pending interventions: none")
        return
    preview = ", ".join(f"{item.step}:{item.type}({item.intervention_id})" for item in pending[:10])
    suffix = " ..." if len(pending) > 10 else ""
    print(f"Pending interventions: {preview}{suffix}")


def _resolve_intervention_step(step_token: str, current_step: int) -> int:
    lowered = step_token.lower()
    if lowered in {"next", "now"}:
        return current_step + 1
    step = int(step_token)
    if step <= current_step:
        raise ValueError(f"Intervention step must be > current step ({current_step})")
    return step


def _parse_intervention_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Intervention payload must be a JSON object")
    return dict(payload)


def _manual_help() -> str:
    return (
        "Commands:\n"
        "  step | s                    run one step\n"
        "  run <n>                     run n steps\n"
        "  runall                      run until configured simulation_steps\n"
        "  add <step|next|now> <type> [json_payload]\n"
        "                              example: add next inject_news '{\"content\":\"x\",\"topic\":\"healthcare\"}'\n"
        "  status                      print runtime status\n"
        "  save                        write outputs now\n"
        "  help                        print this help\n"
        "  quit | exit                 save and exit"
    )


def run_stepwise_scenario(
    config: Path,
    output_dir: Path | None = None,
    seed: int | None = None,
    steps: int | None = None,
    snapshot_each_step: bool | None = None,
    write_decision_trace: bool | None = None,
    scripted_commands: list[str] | None = None,
) -> SimulationState:
    cfg = load_config(config)
    if output_dir is not None:
        cfg.output.output_dir = output_dir
    if seed is not None:
        cfg.simulation.random_seed = int(seed)
    if steps is not None:
        cfg.simulation.simulation_steps = max(1, int(steps))
    if snapshot_each_step is not None:
        cfg.output.snapshot_each_step = bool(snapshot_each_step)
    if write_decision_trace is not None:
        cfg.output.write_decision_trace = bool(write_decision_trace)

    logger = setup_logger(cfg.log_level, cfg.output.output_dir)
    engine, _ = _build_engine(cfg)
    planned_steps = int(cfg.simulation.simulation_steps)
    manual_id_seq = len(engine.state.interventions)
    command_cursor = 0
    reached_plan_notified = False

    print("\n=== VASociety Step Mode ===")
    print(f"Scenario: {cfg.scenario_name}")
    print(f"Run ID: {engine.state.run_id}")
    print(f"Output dir: {cfg.output.output_dir}")
    print(_manual_help())
    _print_runtime_status(engine.state, planned_steps)

    while True:
        if engine.state.current_step >= planned_steps and not reached_plan_notified:
            print(
                f"Reached configured simulation_steps={planned_steps}. "
                "You can still use step/run for extra steps or quit."
            )
            reached_plan_notified = True

        if scripted_commands is None:
            raw_command = input(f"vasociety(step={engine.state.current_step})> ").strip()
        else:
            if command_cursor >= len(scripted_commands):
                raw_command = "quit"
            else:
                raw_command = scripted_commands[command_cursor]
                command_cursor += 1
                print(f"vasociety(step={engine.state.current_step})> {raw_command}")
            raw_command = raw_command.strip()

        if not raw_command:
            continue
        try:
            tokens = shlex.split(raw_command)
        except ValueError as exc:
            print(f"Invalid command syntax: {exc}")
            continue
        if not tokens:
            continue

        command = tokens[0].lower()
        try:
            if command in {"help", "h", "?"}:
                print(_manual_help())
                continue

            if command == "status":
                _print_runtime_status(engine.state, planned_steps)
                continue

            if command in {"step", "s"}:
                engine.step(snapshot_each_step=cfg.output.snapshot_each_step)
                _print_step_summary(engine.state)
                continue

            if command == "runall":
                remaining = max(0, planned_steps - engine.state.current_step)
                if remaining == 0:
                    print("No remaining planned steps. Use step/run to continue manually.")
                else:
                    for _ in range(remaining):
                        engine.step(snapshot_each_step=cfg.output.snapshot_each_step)
                _print_step_summary(engine.state)
                continue

            if command == "run":
                if len(tokens) < 2:
                    raise ValueError("Usage: run <n>")
                count = int(tokens[1])
                if count <= 0:
                    raise ValueError("run count must be >= 1")
                for _ in range(count):
                    engine.step(snapshot_each_step=cfg.output.snapshot_each_step)
                _print_step_summary(engine.state)
                continue

            if command == "add":
                if len(tokens) < 3:
                    raise ValueError("Usage: add <step|next|now> <type> [json_payload]")
                step = _resolve_intervention_step(tokens[1], engine.state.current_step)
                intervention_type = str(tokens[2])
                if intervention_type not in INTERVENTION_TYPES:
                    valid = ", ".join(sorted(INTERVENTION_TYPES))
                    raise ValueError(f"Unsupported intervention type '{intervention_type}', expected one of: {valid}")
                payload = _parse_intervention_payload(" ".join(tokens[3:])) if len(tokens) > 3 else {}
                manual_id_seq += 1
                intervention_id = str(payload.pop("intervention_id", f"manual_{manual_id_seq:03d}"))
                intervention = Intervention(
                    intervention_id=intervention_id,
                    step=step,
                    type=intervention_type,
                    payload=payload,
                )
                engine.schedule_intervention(intervention)
                print(
                    f"Added intervention id={intervention.intervention_id} "
                    f"type={intervention.type} step={intervention.step}"
                )
                continue

            if command == "save":
                save_state(engine.state, cfg.output.output_dir, write_decision_trace=cfg.output.write_decision_trace)
                print(f"Saved outputs to: {cfg.output.output_dir}")
                continue

            if command in {"quit", "exit", "q"}:
                save_state(engine.state, cfg.output.output_dir, write_decision_trace=cfg.output.write_decision_trace)
                latest = engine.state.metrics_history[-1] if engine.state.metrics_history else None
                print("\n=== VASociety Step Summary ===")
                print(f"Run ID: {engine.state.run_id}")
                print(f"Scenario: {cfg.scenario_name}")
                print(f"Current step: {engine.state.current_step}")
                if latest is not None:
                    print(f"Total posts: {latest.total_posts}")
                    print(f"Total comments: {latest.total_comments}")
                    print(f"Discussion heat: {latest.discussion_heat}")
                    print(f"Stance shifts: {latest.stance_shift_count}")
                print(f"Outputs saved to: {cfg.output.output_dir}")
                logger.info(
                    "Step mode completed at step=%s with posts=%s comments=%s",
                    engine.state.current_step,
                    latest.total_posts if latest is not None else 0,
                    latest.total_comments if latest is not None else 0,
                )
                return engine.state

            raise ValueError(f"Unknown command '{tokens[0]}'. Use 'help' for command list.")
        except ValueError as exc:
            print(f"Command error: {exc}")


def _load_experiment_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    else:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Experiment config must be a mapping")
    return dict(payload)


def run_experiment(
    scenarios: list[Path],
    seeds: list[int],
    output_dir: Path,
    steps: int | None = None,
    snapshot_each_step: bool | None = None,
    write_decision_trace: bool | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_summaries: list[dict[str, Any]] = []
    run_index = 1

    for scenario_path in scenarios:
        for seed in seeds:
            run_output_dir = output_dir / f"run_{run_index:03d}"
            state = run_single_scenario(
                config=scenario_path,
                output_dir=run_output_dir,
                seed=seed,
                steps=steps,
                snapshot_each_step=snapshot_each_step,
                write_decision_trace=write_decision_trace,
                emit_summary=False,
            )
            latest = state.metrics_history[-1] if state.metrics_history else None
            run_summaries.append(
                {
                    "run_index": run_index,
                    "run_id": state.run_id,
                    "scenario_path": str(scenario_path),
                    "scenario_name": state.scenario_name,
                    "seed": seed,
                    "output_dir": str(run_output_dir),
                    "steps": state.current_step,
                    "latest_metrics": asdict(latest) if latest is not None else {},
                }
            )
            run_index += 1

    total_runs = len(run_summaries)
    avg_posts = round(
        sum(item["latest_metrics"].get("total_posts", 0) for item in run_summaries) / total_runs if total_runs else 0.0,
        4,
    )
    avg_heat = round(
        sum(item["latest_metrics"].get("discussion_heat", 0.0) for item in run_summaries) / total_runs if total_runs else 0.0,
        4,
    )
    avg_stance_shift = round(
        sum(item["latest_metrics"].get("stance_shift_count", 0) for item in run_summaries) / total_runs if total_runs else 0.0,
        4,
    )
    summary = {
        "schema_version": "experiment_summary.v1",
        "total_runs": total_runs,
        "scenarios": [str(path) for path in scenarios],
        "seeds": list(seeds),
        "avg_total_posts": avg_posts,
        "avg_discussion_heat": avg_heat,
        "avg_stance_shift_count": avg_stance_shift,
        "runs": run_summaries,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== VASociety Experiment Summary ===")
    print(f"Total runs: {total_runs}")
    print(f"Average total posts: {avg_posts}")
    print(f"Average discussion heat: {avg_heat}")
    print(f"Average stance shifts: {avg_stance_shift}")
    print(f"Experiment outputs saved to: {output_dir}")
    return summary


def analyze_output(output_dir: Path, write_files: bool = True) -> dict[str, Any]:
    state = load_runtime_state(output_dir)
    explanation = generate_explanation_summary(state)
    trace_schema = validate_decision_trace_schema(state.decision_trace)
    consistency = metrics_trace_consistency(state)
    report = {
        "schema_version": "analysis_report.v1",
        "run_id": state.run_id,
        "scenario_name": state.scenario_name,
        "steps": state.current_step,
        "trace_schema": trace_schema,
        "metrics_trace_consistency": consistency,
        "explanation_summary": explanation,
    }
    if write_files:
        (output_dir / "analysis_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== VASociety Analyze Summary ===")
    print(f"Run ID: {state.run_id}")
    print(f"Scenario: {state.scenario_name}")
    print(f"Trace schema valid: {trace_schema.get('is_valid')}")
    print(f"Metrics-trace consistent: {consistency.get('is_consistent')}")
    print(f"Analysis report: {output_dir / 'analysis_report.json'}")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VASociety simulation CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a single scenario")
    run_parser.add_argument("--config", "-c", type=Path, default=Path("configs/scenarios/demo.yaml"))
    run_parser.add_argument("--output-dir", type=Path, default=None)
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--steps", type=int, default=None)
    run_parser.add_argument("--snapshot-each-step", action=argparse.BooleanOptionalAction, default=None)
    run_parser.add_argument("--write-decision-trace", action=argparse.BooleanOptionalAction, default=None)

    step_parser = subparsers.add_parser("step", help="Run simulation in interactive step mode")
    step_parser.add_argument("--config", "-c", type=Path, default=Path("configs/scenarios/demo.yaml"))
    step_parser.add_argument("--output-dir", type=Path, default=None)
    step_parser.add_argument("--seed", type=int, default=None)
    step_parser.add_argument("--steps", type=int, default=None)
    step_parser.add_argument("--snapshot-each-step", action=argparse.BooleanOptionalAction, default=None)
    step_parser.add_argument("--write-decision-trace", action=argparse.BooleanOptionalAction, default=None)

    exp_parser = subparsers.add_parser("experiment", help="Run multi-scenario multi-seed experiment")
    exp_parser.add_argument("--experiment-config", type=Path, default=None)
    exp_parser.add_argument("--scenarios", nargs="+", type=Path, default=None)
    exp_parser.add_argument("--seeds", nargs="+", type=int, default=None)
    exp_parser.add_argument("--output-dir", type=Path, default=Path("outputs/experiments/exp_cli"))
    exp_parser.add_argument("--steps", type=int, default=None)
    exp_parser.add_argument("--snapshot-each-step", action=argparse.BooleanOptionalAction, default=None)
    exp_parser.add_argument("--write-decision-trace", action=argparse.BooleanOptionalAction, default=None)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one run output directory")
    analyze_parser.add_argument("--output-dir", type=Path, default=Path("outputs/demo_run"))
    analyze_parser.add_argument("--write-files", action=argparse.BooleanOptionalAction, default=True)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"run", "step", "experiment", "analyze"}
    if not raw_args:
        raw_args = ["run"]
    elif raw_args[0] not in known_commands:
        if raw_args[0].startswith("-"):
            raw_args = ["run", *raw_args]
        else:
            raw_args = ["run", "--config", raw_args[0], *raw_args[1:]]

    args = parser.parse_args(raw_args)
    if args.command == "run":
        run_single_scenario(
            config=args.config,
            output_dir=args.output_dir,
            seed=args.seed,
            steps=args.steps,
            snapshot_each_step=args.snapshot_each_step,
            write_decision_trace=args.write_decision_trace,
            emit_summary=True,
        )
        return

    if args.command == "step":
        run_stepwise_scenario(
            config=args.config,
            output_dir=args.output_dir,
            seed=args.seed,
            steps=args.steps,
            snapshot_each_step=args.snapshot_each_step,
            write_decision_trace=args.write_decision_trace,
        )
        return

    if args.command == "experiment":
        scenarios: list[Path]
        seeds: list[int]
        output_dir: Path
        steps = args.steps
        snapshot_each_step = args.snapshot_each_step
        write_decision_trace = args.write_decision_trace
        if args.experiment_config is not None:
            payload = _load_experiment_payload(args.experiment_config)
            base_dir = args.experiment_config.parent
            scenarios_raw = payload.get("scenarios", [])
            if not isinstance(scenarios_raw, list) or not scenarios_raw:
                raise ValueError("Experiment config requires non-empty 'scenarios' list")
            scenarios = [
                (base_dir / Path(str(item))).resolve() if not Path(str(item)).is_absolute() else Path(str(item))
                for item in scenarios_raw
            ]
            seeds_raw = payload.get("seeds", [7])
            if not isinstance(seeds_raw, list) or not seeds_raw:
                raise ValueError("Experiment config requires non-empty 'seeds' list")
            seeds = [int(item) for item in seeds_raw]
            output_dir = Path(payload.get("output_dir", str(args.output_dir)))
            if not output_dir.is_absolute():
                output_dir = output_dir.resolve()
            if steps is None and "steps" in payload:
                steps = int(payload["steps"])
            if snapshot_each_step is None and "snapshot_each_step" in payload:
                snapshot_each_step = bool(payload["snapshot_each_step"])
            if write_decision_trace is None and "write_decision_trace" in payload:
                write_decision_trace = bool(payload["write_decision_trace"])
        else:
            if not args.scenarios:
                raise ValueError("Use --scenarios or --experiment-config for experiment command")
            scenarios = list(args.scenarios)
            seeds = list(args.seeds or [7])
            output_dir = args.output_dir

        run_experiment(
            scenarios=scenarios,
            seeds=seeds,
            output_dir=output_dir,
            steps=steps,
            snapshot_each_step=snapshot_each_step,
            write_decision_trace=write_decision_trace,
        )
        return

    if args.command == "analyze":
        analyze_output(output_dir=args.output_dir, write_files=bool(args.write_files))
        return


if __name__ == "__main__":
    main()
