"""Output serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vasociety.analytics.explain import build_final_state_summary, generate_explanation_summary
from vasociety.analytics.trace_analyzer import (
    metrics_trace_consistency,
    persona_participation_summary,
    stance_shift_summary,
    top_diffusion_posts,
    topic_heat_over_time,
    validate_decision_trace_schema,
)
from vasociety.models.state import SimulationState


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _compact_records(records: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], bool]:
    if len(records) <= limit:
        return records, False
    return records[:limit], True


def _event_records(event_log: list[dict[str, Any]], event_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event in event_log:
        if event.get("event") != event_name:
            continue
        payload = event.get("payload")
        record: dict[str, Any] = {
            "schema_version": str(event.get("schema_version", "event_log.v1")),
            "step": int(event.get("step", 0)),
            "event": event_name,
        }
        if isinstance(payload, dict):
            record.update(payload)
        else:
            record["payload"] = payload
        for key in (
            "agent_id",
            "selected_action",
            "target_id",
            "decision_reason",
            "visible_item_ids",
            "ranked_reasons",
            "state_delta",
        ):
            if key in event and key not in record:
                record[key] = event[key]
        records.append(record)
    return records


def save_state(state: SimulationState, output_dir: Path, write_decision_trace: bool = True) -> None:
    world_payload = state.world_state.to_dict()
    artifacts_payload = state.run_artifacts.to_dict()
    summary_payload = build_final_state_summary(state)

    post_records = [asdict(post) for post in state.posts.values()]
    comment_records = [asdict(comment) for comment in state.comments.values()]
    compact_posts, posts_truncated = _compact_records(post_records, limit=200)
    compact_comments, comments_truncated = _compact_records(comment_records, limit=200)

    final_state = {
        "schema_version": "final_state.v2",
        **summary_payload,
        "post_count": len(post_records),
        "comment_count": len(comment_records),
        "posts_truncated": posts_truncated,
        "comments_truncated": comments_truncated,
        "posts": compact_posts,
        "comments": compact_comments,
        "social_graph": {
            "followees": state.followees,
            "followers": state.followers,
            "trust_edges": state.trust_edges,
            "affinity_edges": state.affinity_edges,
            "follow_graph": state.follow_graph,
            "trust_graph": state.trust_graph,
            "community_labels": state.community_labels,
        },
        "platform_state": {
            "trending_pool": list(state.trending_pool),
            "official_pinned_content": list(state.official_pinned_content),
            "suppressed_content": list(state.suppressed_content),
        },
        "agents": [
            {
                "agent_id": agent.agent_id,
                "persona_type": agent.persona_type,
                "topic_stances": agent.topic_stances,
                "stance_shift_count": sum(
                    1
                    for record in agent.stance_update_history
                    if str(record.get("from", "")) != str(record.get("to", ""))
                ),
                "action_count": len(agent.action_history),
            }
            for agent in state.agents.values()
        ],
    }

    event_log = state.run_artifacts.event_log
    perception_log = _event_records(event_log, "perception_log")
    decision_log = _event_records(event_log, "decision_log")
    execution_log = _event_records(event_log, "execution_log")
    intervention_log = _event_records(event_log, "intervention")
    metrics_log = _event_records(event_log, "metrics")

    trace_schema_report = validate_decision_trace_schema(state.run_artifacts.decision_trace)
    consistency_report = metrics_trace_consistency(state)
    trace_analysis = {
        "trace_schema": trace_schema_report,
        "metrics_trace_consistency": consistency_report,
        "topic_heat_over_time": topic_heat_over_time(state),
        "stance_shift_summary": stance_shift_summary(state),
        "persona_participation_summary": persona_participation_summary(state),
        "top_diffusion_posts": top_diffusion_posts(state, top_k=10),
    }
    explanation_summary = generate_explanation_summary(state)

    _write_json(output_dir / "world_state.json", world_payload)
    _write_json(output_dir / "run_artifacts.json", artifacts_payload)
    _write_json(output_dir / "final_state.json", final_state)
    _write_json(output_dir / "metrics_history.json", [asdict(metric) for metric in state.run_artifacts.metrics_history])
    _write_jsonl(output_dir / "event_log.jsonl", state.run_artifacts.event_log)
    _write_jsonl(output_dir / "perception_log.jsonl", perception_log)
    _write_jsonl(output_dir / "decision_log.jsonl", decision_log)
    _write_jsonl(output_dir / "execution_log.jsonl", execution_log)
    _write_jsonl(output_dir / "intervention_log.jsonl", intervention_log)
    _write_jsonl(output_dir / "metrics_log.jsonl", metrics_log)
    _write_json(output_dir / "trace_analysis.json", trace_analysis)
    _write_json(output_dir / "explanation_summary.json", explanation_summary)

    if write_decision_trace:
        _write_jsonl(output_dir / "decision_trace.jsonl", state.run_artifacts.decision_trace)
    if state.run_artifacts.snapshots:
        _write_json(output_dir / "snapshots.json", state.run_artifacts.snapshots)
