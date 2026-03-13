"""Typed scenario-driven configuration with YAML-first loading and legacy compatibility."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback path
    yaml = None


SCENARIO_KEYS = {
    "scenario_name",
    "description",
    "topics",
    "initial_population",
    "population_ref",
    "platform_rules",
    "platform_ref",
    "interventions",
    "simulation",
    "simulation_steps",
    "random_seed",
    "log_level",
    "output",
}
LEGACY_KEYS = {
    "seed",
    "steps",
    "log_level",
    "agent_population",
    "feed",
    "interventions",
    "output",
    "output_dir",
    "snapshot_each_step",
    "write_decision_trace",
    "scenario_name",
    "description",
    "topics",
}
SIMULATION_KEYS = {"simulation_steps", "random_seed", "log_level"}
POPULATION_KEYS = {"count", "topics"}
PLATFORM_KEYS = {"feed"}
FEED_KEYS = {"max_items", "view_top_k", "weights", "ranking_strategy"}
WEIGHT_KEYS = {
    "heat",
    "freshness",
    "topic_match",
    "stance_affinity",
    "stance_alignment",
    "official_boost",
    "source_trust",
    "social_proximity",
    "novelty",
}
OUTPUT_KEYS = {"output_dir", "snapshot_each_step", "write_decision_trace"}
INTERVENTION_KEYS = {"intervention_id", "step", "type", "payload"}
RANKING_STRATEGIES = {"hotness_first", "interest_first", "social_first", "balanced"}
INTERVENTION_TYPES = {
    "inject_news",
    "inject_fact_check",
    "platform_boost",
    "platform_suppress",
    "official_pin",
    "targeted_push",
}


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
    ranking_strategy: str = "balanced"
    weights: FeedWeightsConfig = field(default_factory=FeedWeightsConfig)


@dataclass(slots=True)
class PopulationConfig:
    count: int = 20
    topics: list[str] = field(default_factory=lambda: ["general"])


@dataclass(slots=True)
class PlatformConfig:
    feed: FeedConfig = field(default_factory=FeedConfig)


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
    simulation_steps: int = 10
    random_seed: int = 42
    log_level: str = "INFO"

    @property
    def steps(self) -> int:
        return self.simulation_steps

    @property
    def seed(self) -> int:
        return self.random_seed


@dataclass(slots=True)
class ScenarioConfig:
    scenario_name: str = "demo_scenario"
    description: str = ""
    topics: list[str] = field(default_factory=lambda: ["general"])
    initial_population: PopulationConfig = field(default_factory=PopulationConfig)
    platform_rules: PlatformConfig = field(default_factory=PlatformConfig)
    interventions: list[InterventionSpec] = field(default_factory=list)
    output: OutputConfig = field(default_factory=OutputConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    # Backward-compatible aliases used by existing runtime wiring.
    @property
    def seed(self) -> int:
        return self.simulation.random_seed

    @property
    def steps(self) -> int:
        return self.simulation.simulation_steps

    @property
    def log_level(self) -> str:
        return self.simulation.log_level

    @property
    def agent_population(self) -> PopulationConfig:
        return self.initial_population

    @property
    def feed(self) -> FeedConfig:
        return self.platform_rules.feed


# Backward-compatible alias for existing imports.
AgentPopulationConfig = PopulationConfig


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
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Top-level config must be a mapping")
        return parsed
    if suffix in {".yaml", ".yml"}:
        if yaml is not None:
            parsed = yaml.safe_load(text)
            if parsed is None:
                return {}
            if not isinstance(parsed, dict):
                raise ValueError("Top-level config must be a mapping")
            return dict(parsed)
        stripped = text.lstrip()
        if stripped.startswith("{"):
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError("Top-level config must be a mapping")
            return parsed
        return _simple_yaml_load(text)
    raise ValueError(f"Unsupported config format: {path}")


def _as_mapping(raw: Any, field_name: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Field '{field_name}' must be a mapping")
    return dict(raw)


def _as_list(raw: Any, field_name: str) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"Field '{field_name}' must be a list")
    return list(raw)


def _validate_allowed_fields(raw: Mapping[str, Any], allowed: set[str], scope: str) -> None:
    unknown = sorted(set(raw.keys()) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unsupported fields in '{scope}': {joined}")


def _coerce_topics(raw: Any, default: list[str] | None = None) -> list[str]:
    topics: list[str]
    if raw is None:
        topics = list(default or ["general"])
    elif isinstance(raw, str):
        topics = [raw]
    elif isinstance(raw, list):
        topics = [str(item) for item in raw if str(item).strip()]
    else:
        raise ValueError("topics must be a string or list")
    return topics or list(default or ["general"])


def _resolve_ref_payload(config_path: Path, ref: Any, field_name: str) -> dict[str, Any]:
    if ref is None:
        return {}
    ref_path = Path(str(ref))
    if not ref_path.is_absolute():
        ref_path = (config_path.parent / ref_path).resolve()
    if not ref_path.exists():
        raise ValueError(f"Referenced file for '{field_name}' does not exist: {ref_path}")
    return _load_payload(ref_path)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _build_feed_config(feed_raw: dict[str, Any], scope: str) -> FeedConfig:
    _validate_allowed_fields(feed_raw, FEED_KEYS, scope)
    weights_raw = _as_mapping(feed_raw.get("weights", {}), f"{scope}.weights")
    _validate_allowed_fields(weights_raw, WEIGHT_KEYS, f"{scope}.weights")
    ranking_strategy = str(feed_raw.get("ranking_strategy", "balanced"))
    if ranking_strategy not in RANKING_STRATEGIES:
        valid = ", ".join(sorted(RANKING_STRATEGIES))
        raise ValueError(f"Unsupported ranking_strategy '{ranking_strategy}', expected one of: {valid}")
    return FeedConfig(
        max_items=max(1, int(feed_raw.get("max_items", 8))),
        view_top_k=max(1, int(feed_raw.get("view_top_k", 3))),
        ranking_strategy=ranking_strategy,
        weights=FeedWeightsConfig(
            heat=float(weights_raw.get("heat", 1.2)),
            freshness=float(weights_raw.get("freshness", 0.8)),
            topic_match=float(weights_raw.get("topic_match", 1.3)),
            stance_affinity=float(weights_raw.get("stance_affinity", weights_raw.get("stance_alignment", 0.5))),
            official_boost=float(weights_raw.get("official_boost", 1.5)),
            source_trust=float(weights_raw.get("source_trust", 0.2)),
            social_proximity=float(weights_raw.get("social_proximity", 0.1)),
            novelty=float(weights_raw.get("novelty", 0.3)),
        ),
    )


def _build_population_config(pop_raw: dict[str, Any], default_topics: list[str]) -> PopulationConfig:
    _validate_allowed_fields(pop_raw, POPULATION_KEYS, "initial_population")
    topics = _coerce_topics(pop_raw.get("topics"), default=default_topics)
    return PopulationConfig(
        count=max(1, int(pop_raw.get("count", 20))),
        topics=topics,
    )


def _build_interventions(raw: list[Any]) -> list[InterventionSpec]:
    specs: list[InterventionSpec] = []
    for idx, item in enumerate(raw):
        scope = f"interventions[{idx}]"
        item_raw = _as_mapping(item, scope)
        _validate_allowed_fields(item_raw, INTERVENTION_KEYS, scope)
        missing = [key for key in ("intervention_id", "step", "type") if key not in item_raw]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required fields in '{scope}': {joined}")
        intervention_type = str(item_raw["type"])
        if intervention_type not in INTERVENTION_TYPES:
            valid = ", ".join(sorted(INTERVENTION_TYPES))
            raise ValueError(f"Unsupported intervention type '{intervention_type}', expected one of: {valid}")
        specs.append(
            InterventionSpec(
                intervention_id=str(item_raw["intervention_id"]),
                step=max(1, int(item_raw["step"])),
                type=intervention_type,
                payload=_as_mapping(item_raw.get("payload", {}), f"{scope}.payload"),
            )
        )
    return specs


def _build_output_config(raw: dict[str, Any]) -> OutputConfig:
    _validate_allowed_fields(raw, OUTPUT_KEYS, "output")
    return OutputConfig(
        output_dir=Path(raw.get("output_dir", "outputs/demo_run")),
        snapshot_each_step=bool(raw.get("snapshot_each_step", True)),
        write_decision_trace=bool(raw.get("write_decision_trace", True)),
    )


def _is_legacy_payload(payload: dict[str, Any]) -> bool:
    legacy_markers = {"seed", "steps", "agent_population", "feed"}
    scenario_markers = {"initial_population", "platform_rules", "simulation", "simulation_steps", "random_seed"}
    if any(key in payload for key in scenario_markers):
        return False
    if any(key in payload for key in legacy_markers):
        return True
    return False


def _migrate_legacy_payload(payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    _validate_allowed_fields(payload, LEGACY_KEYS, "legacy_config")

    agent_raw = _as_mapping(payload.get("agent_population", {}), "agent_population")
    feed_raw = _as_mapping(payload.get("feed", {}), "feed")

    output_raw = _as_mapping(payload.get("output", {}), "output")
    if "output_dir" in payload:
        output_raw.setdefault("output_dir", payload["output_dir"])
    if "snapshot_each_step" in payload:
        output_raw.setdefault("snapshot_each_step", payload["snapshot_each_step"])
    if "write_decision_trace" in payload:
        output_raw.setdefault("write_decision_trace", payload["write_decision_trace"])

    topics = _coerce_topics(payload.get("topics", agent_raw.get("topics")), default=["general"])
    migrated = {
        "scenario_name": str(payload.get("scenario_name", source_path.stem)),
        "description": str(payload.get("description", "Migrated from legacy demo-style config.")),
        "topics": topics,
        "initial_population": {
            "count": agent_raw.get("count", 20),
            "topics": agent_raw.get("topics", topics),
        },
        "platform_rules": {"feed": feed_raw},
        "interventions": _as_list(payload.get("interventions", []), "interventions"),
        "simulation": {
            "random_seed": payload.get("seed", 42),
            "simulation_steps": payload.get("steps", 10),
            "log_level": payload.get("log_level", "INFO"),
        },
        "output": output_raw,
    }
    return migrated


def _parse_scenario_payload(payload: dict[str, Any], source_path: Path) -> ScenarioConfig:
    _validate_allowed_fields(payload, SCENARIO_KEYS, "scenario")

    ref_population = _resolve_ref_payload(source_path, payload.get("population_ref"), "population_ref")
    ref_platform = _resolve_ref_payload(source_path, payload.get("platform_ref"), "platform_ref")

    inline_population = _as_mapping(payload.get("initial_population", {}), "initial_population")
    inline_platform = _as_mapping(payload.get("platform_rules", {}), "platform_rules")
    population_raw = _deep_merge(ref_population, inline_population)
    platform_raw = _deep_merge(ref_platform, inline_platform)

    topics = _coerce_topics(payload.get("topics", population_raw.get("topics")), default=["general"])
    population_cfg = _build_population_config(population_raw, default_topics=topics)

    _validate_allowed_fields(platform_raw, PLATFORM_KEYS, "platform_rules")
    feed_raw = _as_mapping(platform_raw.get("feed", {}), "platform_rules.feed")
    platform_cfg = PlatformConfig(feed=_build_feed_config(feed_raw, scope="platform_rules.feed"))

    simulation_raw = _as_mapping(payload.get("simulation", {}), "simulation")
    _validate_allowed_fields(simulation_raw, SIMULATION_KEYS, "simulation")
    simulation_cfg = SimulationConfig(
        random_seed=int(payload.get("random_seed", simulation_raw.get("random_seed", 42))),
        simulation_steps=max(1, int(payload.get("simulation_steps", simulation_raw.get("simulation_steps", 10)))),
        log_level=str(payload.get("log_level", simulation_raw.get("log_level", "INFO"))),
    )

    output_cfg = _build_output_config(_as_mapping(payload.get("output", {}), "output"))
    interventions_cfg = _build_interventions(_as_list(payload.get("interventions", []), "interventions"))

    return ScenarioConfig(
        scenario_name=str(payload.get("scenario_name", source_path.stem)),
        description=str(payload.get("description", "")),
        topics=topics,
        initial_population=population_cfg,
        platform_rules=platform_cfg,
        interventions=interventions_cfg,
        output=output_cfg,
        simulation=simulation_cfg,
    )


def load_config(path: Path) -> ScenarioConfig:
    payload = _load_payload(path)
    scenario_payload = _migrate_legacy_payload(payload, path) if _is_legacy_payload(payload) else payload
    return _parse_scenario_payload(scenario_payload, path)
