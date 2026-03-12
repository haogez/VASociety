"""Scheduling helper for interventions by simulation step."""

from __future__ import annotations

from collections import defaultdict

from vasociety.models.intervention import Intervention


class InterventionScheduler:
    """Index interventions for quick retrieval each step."""

    def __init__(self, interventions: list[Intervention]) -> None:
        self._index: dict[int, list[Intervention]] = defaultdict(list)
        for intervention in interventions:
            self._index[intervention.step].append(intervention)

    def get_for_step(self, step: int) -> list[Intervention]:
        return list(self._index.get(step, []))
