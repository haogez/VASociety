"""Scheduling helper for interventions by simulation step."""

from __future__ import annotations

from collections import defaultdict

from vasociety.models.intervention import Intervention


class InterventionScheduler:
    """Index interventions for quick retrieval each step."""

    def __init__(self, interventions: list[Intervention]) -> None:
        self._index: dict[int, list[Intervention]] = defaultdict(list)
        self.add_many(interventions)

    def get_for_step(self, step: int) -> list[Intervention]:
        return list(self._index.get(step, []))

    def add_intervention(self, intervention: Intervention) -> None:
        self._index[int(intervention.step)].append(intervention)

    def add_many(self, interventions: list[Intervention]) -> None:
        for intervention in interventions:
            self.add_intervention(intervention)
