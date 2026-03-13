from pathlib import Path

import pytest

from vasociety.config import load_config


def test_load_scenario_yaml_config(tmp_path: Path) -> None:
    p = tmp_path / "scenario.yaml"
    p.write_text(
        """
scenario_name: baseline_case
description: baseline
topics: [healthcare, economy]
simulation_steps: 4
random_seed: 9
initial_population:
  count: 5
platform_rules:
  feed:
    max_items: 6
    view_top_k: 2
interventions: []
output:
  output_dir: outputs/x
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.scenario_name == "baseline_case"
    assert cfg.simulation.simulation_steps == 4
    assert cfg.simulation.random_seed == 9
    assert cfg.platform_rules.feed.view_top_k == 2
    assert cfg.initial_population.topics == ["healthcare", "economy"]


def test_load_scenario_with_refs(tmp_path: Path) -> None:
    pop = tmp_path / "population.yaml"
    pop.write_text("count: 7\ntopics: [t1, t2]\n", encoding="utf-8")
    platform = tmp_path / "platform.yaml"
    platform.write_text("feed:\n  view_top_k: 4\n", encoding="utf-8")

    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        """
scenario_name: ref_case
population_ref: population.yaml
platform_ref: platform.yaml
interventions: []
""",
        encoding="utf-8",
    )
    cfg = load_config(scenario)
    assert cfg.initial_population.count == 7
    assert cfg.platform_rules.feed.view_top_k == 4
    assert cfg.topics == ["t1", "t2"]


def test_load_legacy_json_back_compat(tmp_path: Path) -> None:
    p = tmp_path / "legacy.json"
    p.write_text(
        '{"seed":2,"steps":3,"agent_population":{"count":2},"interventions":[]}',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.steps == 3
    assert cfg.agent_population.count == 2


def test_defaults_for_missing_fields(tmp_path: Path) -> None:
    p = tmp_path / "minimal.yaml"
    p.write_text("scenario_name: minimal\ninterventions: []\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.topics == ["general"]
    assert cfg.initial_population.count == 20
    assert cfg.platform_rules.feed.max_items == 8
    assert cfg.platform_rules.feed.ranking_strategy == "balanced"
    assert cfg.simulation.simulation_steps == 10
    assert cfg.output.write_decision_trace is True


def test_feed_ranking_strategy_loaded(tmp_path: Path) -> None:
    p = tmp_path / "strategy.yaml"
    p.write_text(
        """
scenario_name: strategy_case
platform_rules:
  feed:
    ranking_strategy: social_first
interventions: []
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.platform_rules.feed.ranking_strategy == "social_first"


def test_invalid_ranking_strategy_raises_error(tmp_path: Path) -> None:
    p = tmp_path / "bad_strategy.yaml"
    p.write_text(
        """
scenario_name: bad_strategy
platform_rules:
  feed:
    ranking_strategy: unknown_strategy
interventions: []
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unsupported ranking_strategy"):
        load_config(p)


def test_invalid_field_raises_error(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("scenario_name: bad\nunknown_field: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported fields"):
        load_config(p)


def test_intervention_type_validation_accepts_governance_types(tmp_path: Path) -> None:
    p = tmp_path / "governance.yaml"
    p.write_text(
        """
scenario_name: governance_case
interventions:
  - intervention_id: pin_1
    step: 2
    type: official_pin
    payload:
      post_id: post_00001
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.interventions[0].type == "official_pin"


def test_intervention_type_validation_rejects_unknown_type(tmp_path: Path) -> None:
    p = tmp_path / "bad_intervention.yaml"
    p.write_text(
        """
scenario_name: bad_intervention
interventions:
  - intervention_id: x1
    step: 1
    type: unknown_type
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unsupported intervention type"):
        load_config(p)


def test_backward_compat_output_fields(tmp_path: Path) -> None:
    p = tmp_path / "legacy.yaml"
    p.write_text(
        '{"seed":1,"steps":2,"output_dir":"outputs/z","snapshot_each_step":false,"interventions":[]}',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert str(cfg.output.output_dir) == "outputs/z"
    assert cfg.output.snapshot_each_step is False
