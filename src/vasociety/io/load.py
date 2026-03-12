"""Input parsing utilities."""

from __future__ import annotations

from vasociety.models.intervention import Intervention


def parse_interventions(raw: list[dict]) -> list[Intervention]:
    """Parse config interventions into typed dataclass instances."""

    return [
        Intervention(
            intervention_id=item["intervention_id"],
            step=int(item["step"]),
            type=item["type"],
            payload=dict(item.get("payload", {})),
        )
        for item in raw
    ]
