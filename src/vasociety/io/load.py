"""Input parsing utilities."""

from __future__ import annotations

from vasociety.config import InterventionSpec
from vasociety.models.intervention import Intervention


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
