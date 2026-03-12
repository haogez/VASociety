"""Configuration loading for simulation runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SimulationConfig:
    """Runtime configuration for the phase-1 simulation engine."""

    seed: int
    steps: int
    output_dir: Path
    log_level: str
    snapshot_each_step: bool
    agent_population: dict[str, Any]
    feed: dict[str, Any]
    interventions: list[dict[str, Any]]


def load_config(path: Path) -> SimulationConfig:
    """Load config payload (JSON syntax, compatible with .yaml filename)."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return SimulationConfig(
        seed=int(payload.get("seed", 42)),
        steps=int(payload.get("steps", 10)),
        output_dir=Path(payload.get("output_dir", "outputs/run")),
        log_level=str(payload.get("log_level", "INFO")),
        snapshot_each_step=bool(payload.get("snapshot_each_step", False)),
        agent_population=dict(payload.get("agent_population", {})),
        feed=dict(payload.get("feed", {})),
        interventions=list(payload.get("interventions", [])),
    )
