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


def save_state(state: SimulationState, output_dir: Path) -> None:
    """Persist final state, metrics, and event logs."""

    final_state = {
        "current_step": state.current_step,
        "posts": [asdict(p) for p in state.posts.values()],
        "comments": [asdict(c) for c in state.comments.values()],
        "agents": [
            {
                "agent_id": a.agent_id,
                "persona_type": a.persona_type,
                "is_online": a.is_online,
                "created_post_ids": a.created_post_ids,
                "seen_content_count": len(a.seen_content_ids),
                "action_count": len(a.action_history),
            }
            for a in state.agents.values()
        ],
    }
    _write_json(output_dir / "final_state.json", final_state)
    _write_json(output_dir / "metrics_history.json", [asdict(m) for m in state.metrics_history])

    event_path = output_dir / "event_log.jsonl"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("w", encoding="utf-8") as f:
        for event in state.event_log:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    if state.snapshots:
        _write_json(output_dir / "snapshots.json", state.snapshots)
