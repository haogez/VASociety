"""Output serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vasociety.models.state import SimulationState


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_state(state: SimulationState, output_dir: Path, write_decision_trace: bool = True) -> None:
    final_state = {
        "current_step": state.current_step,
        "posts": [asdict(post) for post in state.posts.values()],
        "comments": [asdict(comment) for comment in state.comments.values()],
        "agents": [
            {
                "agent_id": agent.agent_id,
                "persona_type": agent.persona_type,
                "topic_beliefs": agent.topic_beliefs,
                "topic_stances": agent.topic_stances,
                "stance_update_history": agent.stance_update_history[-10:],
                "created_post_ids": agent.created_post_ids,
                "seen_content_count": len(agent.seen_content_ids),
                "action_count": len(agent.action_history),
            }
            for agent in state.agents.values()
        ],
    }
    _write_json(output_dir / "final_state.json", final_state)
    _write_json(output_dir / "metrics_history.json", [asdict(metric) for metric in state.metrics_history])
    _write_jsonl(output_dir / "event_log.jsonl", state.event_log)

    if write_decision_trace:
        _write_jsonl(output_dir / "decision_trace.jsonl", state.decision_trace)
    if state.snapshots:
        _write_json(output_dir / "snapshots.json", state.snapshots)
