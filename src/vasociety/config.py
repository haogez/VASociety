"""Typed configuration system with YAML-first loading and JSON compatibility."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback path
    yaml = None


@dataclass(slots=True)
class AgentPopulationConfig:
    count: int = 20
    topics: list[str] = field(default_factory=lambda: ["general"])


@dataclass(slots=True)
class FeedWeightsConfig:
    heat: float = 1.2
    freshness: float = 0.8
    topic_match: float = 1.3
    stance_affinity: float = 0.5
    official_boost: float = 1.5
    source_trust: float = 0.2
    social_proximity: float = 0.1
    novelty: float = 0.3


@dataclass(slots=True)
class FeedConfig:
    max_items: int = 8
    view_top_k: int = 3
    weights: FeedWeightsConfig = field(default_factory=FeedWeightsConfig)


@dataclass(slots=True)
class InterventionSpec:
    intervention_id: str
    step: int
    type: str
    payload: dict[str, Any]


@dataclass(slots=True)
class OutputConfig:
    output_dir: Path = Path("outputs/demo_run")
    snapshot_each_step: bool = True
    write_decision_trace: bool = True


@dataclass(slots=True)
class SimulationConfig:
    seed: int = 42
    steps: int = 10
    log_level: str = "INFO"
    agent_population: AgentPopulationConfig = field(default_factory=AgentPopulationConfig)
    feed: FeedConfig = field(default_factory=FeedConfig)
    interventions: list[InterventionSpec] = field(default_factory=list)
    output: OutputConfig = field(default_factory=OutputConfig)


def _simple_yaml_load(text: str) -> dict[str, Any]:
    """Very small YAML subset parser used only when PyYAML is unavailable."""

    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    def parse_scalar(v: str) -> Any:
        if v in {"true", "True"}:
            return True
        if v in {"false", "False"}:
            return False
        if v in {"[]", "{}"}:
            return json.loads(v)
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        if v.startswith("'") and v.endswith("'"):
            return v[1:-1]
        if v.startswith("[") or v.startswith("{"):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        try:
            if "." in v:
                return float(v)
            return int(v)
        except ValueError:
            return v

    def parse_block(idx: int, indent: int) -> tuple[Any, int]:
        mapping: dict[str, Any] = {}
        sequence: list[Any] | None = None
        while idx < len(lines):
            line = lines[idx]
            cur_indent = len(line) - len(line.lstrip(" "))
            if cur_indent < indent:
                break
            stripped = line.strip()
            if stripped.startswith("- "):
                if sequence is None:
                    sequence = []
                item = stripped[2:]
                if ":" in item and not item.endswith(":"):
                    k, v = item.split(":", 1)
                    sequence.append({k.strip(): parse_scalar(v.strip())})
                    idx += 1
                elif item.endswith(":") or item == "":
                    idx += 1
                    obj, idx = parse_block(idx, cur_indent + 2)
                    if item.endswith(":") and item != "":
                        sequence.append({item[:-1].strip(): obj})
                    else:
                        sequence.append(obj)
                else:
                    sequence.append(parse_scalar(item))
                    idx += 1
                continue

            if sequence is not None:
                break

            if ":" not in stripped:
                idx += 1
                continue
            key, raw = stripped.split(":", 1)
            key = key.strip()
            raw = raw.strip()
            if raw == "":
                idx += 1
                value, idx = parse_block(idx, cur_indent + 2)
                mapping[key] = value
            else:
                mapping[key] = parse_scalar(raw)
                idx += 1
        return (sequence if sequence is not None else mapping), idx

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("Top-level config must be a mapping")
    return parsed


def _load_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".json"}:
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        if yaml is not None:
            parsed = yaml.safe_load(text)
            return dict(parsed or {})
        stripped = text.lstrip()
        if stripped.startswith("{"):
            return json.loads(text)
        return _simple_yaml_load(text)
    raise ValueError(f"Unsupported config format: {path}")


def load_config(path: Path) -> SimulationConfig:
    payload = _load_payload(path)

    agent_raw = payload.get("agent_population", {})
    feed_raw = payload.get("feed", {})
    weights_raw = feed_raw.get("weights", {})
    output_raw = payload.get("output", {})
    if "output_dir" in payload:  # backward compatibility
        output_raw.setdefault("output_dir", payload["output_dir"])
    if "snapshot_each_step" in payload:
        output_raw.setdefault("snapshot_each_step", payload["snapshot_each_step"])

    cfg = SimulationConfig(
        seed=int(payload.get("seed", 42)),
        steps=max(1, int(payload.get("steps", 10))),
        log_level=str(payload.get("log_level", "INFO")),
        agent_population=AgentPopulationConfig(
            count=max(1, int(agent_raw.get("count", 20))),
            topics=list(agent_raw.get("topics", ["general"])) or ["general"],
        ),
        feed=FeedConfig(
            max_items=max(1, int(feed_raw.get("max_items", 8))),
            view_top_k=max(1, int(feed_raw.get("view_top_k", 3))),
            weights=FeedWeightsConfig(
                heat=float(weights_raw.get("heat", 1.2)),
                freshness=float(weights_raw.get("freshness", 0.8)),
                topic_match=float(weights_raw.get("topic_match", 1.3)),
                stance_affinity=float(
                    weights_raw.get("stance_affinity", weights_raw.get("stance_alignment", 0.5))
                ),
                official_boost=float(weights_raw.get("official_boost", 1.5)),
                source_trust=float(weights_raw.get("source_trust", 0.2)),
                social_proximity=float(weights_raw.get("social_proximity", 0.1)),
                novelty=float(weights_raw.get("novelty", 0.3)),
            ),
        ),
        interventions=[
            InterventionSpec(
                intervention_id=str(item["intervention_id"]),
                step=max(1, int(item["step"])),
                type=str(item["type"]),
                payload=dict(item.get("payload", {})),
            )
            for item in payload.get("interventions", [])
        ],
        output=OutputConfig(
            output_dir=Path(output_raw.get("output_dir", "outputs/demo_run")),
            snapshot_each_step=bool(output_raw.get("snapshot_each_step", True)),
            write_decision_trace=bool(output_raw.get("write_decision_trace", True)),
        ),
    )
    return cfg
