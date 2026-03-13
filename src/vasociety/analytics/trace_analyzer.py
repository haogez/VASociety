"""Trace analysis helpers for experiment-grade outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from vasociety.models.metrics import MetricsSnapshot
from vasociety.models.state import SimulationState


def _metrics_iter(source: SimulationState | Iterable[MetricsSnapshot]) -> list[MetricsSnapshot]:
    if isinstance(source, SimulationState):
        return list(source.metrics_history)
    return list(source)


def topic_heat_over_time(source: SimulationState | Iterable[MetricsSnapshot]) -> dict[str, list[dict[str, float | int]]]:
    """Return topic heat curves keyed by topic."""

    series: dict[str, list[dict[str, float | int]]] = defaultdict(list)
    for snapshot in _metrics_iter(source):
        for topic, value in snapshot.per_step_topic_heat.items():
            series[str(topic)].append({"step": int(snapshot.step), "heat": float(value)})
    for topic in series:
        series[topic].sort(key=lambda item: int(item["step"]))
    return dict(series)


def stance_shift_summary(state: SimulationState) -> dict[str, Any]:
    """Aggregate stance shifts by topic, agent and transition."""

    by_topic: Counter[str] = Counter()
    by_agent: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for agent_id, agent in state.agents.items():
        for record in agent.stance_update_history:
            topic = str(record.get("topic", "unknown"))
            old_stance = str(record.get("from", "unknown"))
            new_stance = str(record.get("to", "unknown"))
            if old_stance == new_stance:
                continue
            by_topic[topic] += 1
            by_agent[agent_id] += 1
            transitions[f"{old_stance}->{new_stance}"] += 1
            if len(examples) < 10:
                examples.append(
                    {
                        "agent_id": agent_id,
                        "topic": topic,
                        "from": old_stance,
                        "to": new_stance,
                        "step": int(record.get("step", 0)),
                        "belief": float(record.get("belief", 0.0)),
                    }
                )

    return {
        "total_shifts": int(sum(by_topic.values())),
        "by_topic": dict(by_topic),
        "by_agent": dict(by_agent),
        "transition_counts": dict(transitions),
        "examples": examples,
    }


def persona_participation_summary(source: SimulationState | Iterable[MetricsSnapshot]) -> dict[str, Any]:
    """Summarize persona participation and per-persona action distributions."""

    total_participation: Counter[str] = Counter()
    total_actions: dict[str, Counter[str]] = defaultdict(Counter)
    by_step: list[dict[str, Any]] = []

    for snapshot in _metrics_iter(source):
        total_participation.update(snapshot.persona_participation)
        for persona, action_map in snapshot.per_persona_action_distribution.items():
            total_actions[persona].update(action_map)
        by_step.append(
            {
                "step": int(snapshot.step),
                "persona_participation": dict(snapshot.persona_participation),
                "per_persona_action_distribution": {
                    persona: dict(actions)
                    for persona, actions in snapshot.per_persona_action_distribution.items()
                },
            }
        )

    return {
        "total_persona_participation": dict(total_participation),
        "total_per_persona_action_distribution": {
            persona: dict(actions) for persona, actions in total_actions.items()
        },
        "by_step": by_step,
    }


def top_diffusion_posts(state: SimulationState, top_k: int = 5) -> list[dict[str, Any]]:
    """Return top posts by diffusion-related score."""

    scored: list[tuple[float, dict[str, Any]]] = []
    for post in state.posts.values():
        path_length = len(post.diffusion_path)
        diffusion_depth = max(0, path_length - 1)
        score = float(post.reposts) * 2.0 + float(post.comments_count) * 1.2 + float(post.exposure_count) * 0.08 + float(
            diffusion_depth
        ) * 0.5
        scored.append(
            (
                score,
                {
                    "post_id": post.post_id,
                    "origin_post_id": post.origin_post_id or post.post_id,
                    "parent_post_id": post.parent_post_id,
                    "author_id": post.author_id,
                    "topic": post.topic,
                    "stance": post.stance,
                    "reposts": int(post.reposts),
                    "comments_count": int(post.comments_count),
                    "exposure_count": int(post.exposure_count),
                    "diffusion_path_length": path_length,
                    "diffusion_depth": diffusion_depth,
                    "diffusion_score": round(score, 4),
                },
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in scored[: max(1, top_k)]]


def validate_decision_trace_schema(decision_trace: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate decision trace schema and return a compact report."""

    required_keys = {
        "step",
        "agent_id",
        "visible_item_ids",
        "ranked_reasons",
        "selected_action",
        "target_id",
        "decision_reason",
        "state_delta",
        "execution",
    }
    valid_records = 0
    invalid_examples: list[dict[str, Any]] = []

    for index, record in enumerate(decision_trace):
        if not isinstance(record, dict):
            if len(invalid_examples) < 5:
                invalid_examples.append({"index": index, "reason": "record_not_mapping"})
            continue
        missing = sorted(required_keys - set(record.keys()))
        execution = record.get("execution")
        execution_ok = isinstance(execution, dict) and "status" in execution and "action" in execution
        if not missing and execution_ok:
            valid_records += 1
            continue
        if len(invalid_examples) < 5:
            invalid_examples.append(
                {
                    "index": index,
                    "missing_keys": missing,
                    "execution_valid": execution_ok,
                }
            )

    total = len(decision_trace)
    invalid_count = total - valid_records
    return {
        "total_records": total,
        "valid_records": valid_records,
        "invalid_records": invalid_count,
        "is_valid": invalid_count == 0,
        "invalid_examples": invalid_examples,
    }


def metrics_trace_consistency(state: SimulationState) -> dict[str, Any]:
    """Cross-check metrics snapshots and decision trace counts."""

    checks: list[dict[str, Any]] = []
    if not state.metrics_history:
        return {"is_consistent": True, "checks": [], "summary": {"reason": "empty_metrics"}}

    decisions_by_step: Counter[int] = Counter()
    action_counts: Counter[str] = Counter()
    for record in state.decision_trace:
        if not isinstance(record, dict):
            continue
        execution = record.get("execution")
        if not isinstance(execution, dict):
            continue
        step = int(record.get("step", 0))
        if str(execution.get("status", "")) == "rejected":
            continue
        decisions_by_step[step] += 1
        action = str(execution.get("action", record.get("selected_action", "")))
        action_counts[action] += 1

    for snapshot in state.metrics_history:
        expected = int(decisions_by_step.get(snapshot.step, 0))
        actual = int(snapshot.active_agents)
        checks.append(
            {
                "name": "active_agents_match_trace",
                "step": int(snapshot.step),
                "ok": expected == actual,
                "expected": expected,
                "actual": actual,
            }
        )

    latest = state.metrics_history[-1]
    checks.extend(
        [
            {
                "name": "comments_total_match",
                "ok": int(latest.total_comments) == len(state.comments),
                "expected": int(latest.total_comments),
                "actual": len(state.comments),
            },
            {
                "name": "likes_total_match",
                "ok": int(latest.total_likes) == sum(post.likes for post in state.posts.values()),
                "expected": int(latest.total_likes),
                "actual": sum(post.likes for post in state.posts.values()),
            },
            {
                "name": "reposts_total_match",
                "ok": int(latest.total_reposts) == sum(post.reposts for post in state.posts.values()),
                "expected": int(latest.total_reposts),
                "actual": sum(post.reposts for post in state.posts.values()),
            },
            {
                "name": "trace_comment_count_match",
                "ok": int(latest.total_comments) == int(action_counts.get("comment", 0)),
                "expected": int(latest.total_comments),
                "actual": int(action_counts.get("comment", 0)),
            },
        ]
    )

    all_ok = all(bool(item.get("ok")) for item in checks)
    return {
        "is_consistent": all_ok,
        "checks": checks,
        "summary": {
            "metrics_steps": len(state.metrics_history),
            "trace_records": len(state.decision_trace),
            "non_rejected_trace_records": int(sum(decisions_by_step.values())),
            "action_counts": dict(action_counts),
        },
    }
