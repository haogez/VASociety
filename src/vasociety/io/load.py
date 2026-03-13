"""Input parsing and output loading utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vasociety.config import InterventionSpec
from vasociety.models.intervention import Intervention
from vasociety.models.state import RunArtifacts, SimulationState, WorldState


def parse_interventions(raw: list[InterventionSpec] | list[dict]) -> list[Intervention]:
    parsed: list[Intervention] = []
    for item in raw:
        if isinstance(item, InterventionSpec):
            parsed.append(
                Intervention(
                    intervention_id=item.intervention_id,
                    step=item.step,
                    type=item.type,
                    payload=dict(item.payload),
                )
            )
        else:
            parsed.append(
                Intervention(
                    intervention_id=str(item["intervention_id"]),
                    step=int(item["step"]),
                    type=str(item["type"]),
                    payload=dict(item.get("payload", {})),
                )
            )
    return parsed


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(dict(json.loads(stripped)))
    return records


def load_world_state(path: Path) -> WorldState:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("world_state payload must be a mapping")
    return WorldState.from_dict(payload)


def load_run_artifacts(path: Path) -> RunArtifacts:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("run_artifacts payload must be a mapping")
    return RunArtifacts.from_dict(payload)


def load_runtime_state(output_dir: Path) -> SimulationState:
    world_state_path = output_dir / "world_state.json"
    run_artifacts_path = output_dir / "run_artifacts.json"
    final_state_path = output_dir / "final_state.json"

    if world_state_path.exists():
        world_state = load_world_state(world_state_path)
    elif final_state_path.exists():
        final_state = _read_json(final_state_path)
        if not isinstance(final_state, dict):
            raise ValueError("final_state payload must be a mapping")
        world_state = WorldState.from_dict(_legacy_world_payload(final_state))
    else:
        world_state = WorldState()

    if run_artifacts_path.exists():
        run_artifacts = load_run_artifacts(run_artifacts_path)
    else:
        run_artifacts = RunArtifacts.from_dict(
            {
                "metrics_history": _read_json(output_dir / "metrics_history.json")
                if (output_dir / "metrics_history.json").exists()
                else [],
                "event_log": _read_jsonl(output_dir / "event_log.jsonl"),
                "decision_trace": _read_jsonl(output_dir / "decision_trace.jsonl"),
                "snapshots": _read_json(output_dir / "snapshots.json")
                if (output_dir / "snapshots.json").exists()
                else [],
            }
        )

    run_id = "run_00001"
    scenario_name = "default_scenario"
    if final_state_path.exists():
        final_state = _read_json(final_state_path)
        if isinstance(final_state, dict):
            run_id = str(final_state.get("run_id", run_id))
            scenario_name = str(final_state.get("scenario_name", scenario_name))

    return SimulationState(
        run_id=run_id,
        scenario_name=scenario_name,
        world_state=world_state,
        run_artifacts=run_artifacts,
        interventions=[],
    )


def _legacy_world_payload(final_state: dict[str, Any]) -> dict[str, Any]:
    posts = {
        str(item["post_id"]): dict(item)
        for item in _as_list(final_state.get("posts", []))
        if isinstance(item, dict) and "post_id" in item
    }
    comments = {
        str(item["comment_id"]): dict(item)
        for item in _as_list(final_state.get("comments", []))
        if isinstance(item, dict) and "comment_id" in item
    }
    social_graph = dict(final_state.get("social_graph", {})) if isinstance(final_state.get("social_graph"), dict) else {}
    platform_state = dict(final_state.get("platform_state", {})) if isinstance(final_state.get("platform_state"), dict) else {}
    return {
        "current_step": int(final_state.get("current_step", 0)),
        "agents": {},
        "posts": posts,
        "comments": comments,
        "stance_shift_count": 0,
        "followees": dict(social_graph.get("followees", social_graph.get("follow_graph", {})))
        if isinstance(social_graph.get("followees", social_graph.get("follow_graph", {})), dict)
        else {},
        "followers": dict(social_graph.get("followers", {})) if isinstance(social_graph.get("followers"), dict) else {},
        "trust_edges": dict(social_graph.get("trust_edges", social_graph.get("trust_graph", {})))
        if isinstance(social_graph.get("trust_edges", social_graph.get("trust_graph", {})), dict)
        else {},
        "affinity_edges": dict(social_graph.get("affinity_edges", {}))
        if isinstance(social_graph.get("affinity_edges"), dict)
        else {},
        "community_labels": dict(social_graph.get("community_labels", {}))
        if isinstance(social_graph.get("community_labels"), dict)
        else {},
        "trending_pool": list(platform_state.get("trending_pool", []))
        if isinstance(platform_state.get("trending_pool"), list)
        else [],
        "official_pinned_content": list(platform_state.get("official_pinned_content", []))
        if isinstance(platform_state.get("official_pinned_content"), list)
        else [],
        "suppressed_content": list(platform_state.get("suppressed_content", []))
        if isinstance(platform_state.get("suppressed_content"), list)
        else [],
    }


def _as_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Expected list payload")
    return list(raw)
