"""Intervention model for external control events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vasociety.types import InterventionType


@dataclass(slots=True)
class Intervention:
    """Scheduled intervention event."""

    intervention_id: str
    step: int
    type: InterventionType
    payload: dict[str, Any] = field(default_factory=dict)
