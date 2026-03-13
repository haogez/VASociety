import json
from pathlib import Path

from vasociety.cli.main import run_single_scenario


def test_smoke_from_scenario_generates_outputs_and_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "smoke_output"
    scenario = tmp_path / "smoke.yaml"
    scenario.write_text(
        f"""
scenario_name: smoke_case
description: smoke scenario
topics: [healthcare]
simulation_steps: 3
random_seed: 7
initial_population:
  count: 5
  topics: [healthcare]
platform_rules:
  feed:
    max_items: 6
    view_top_k: 2
    ranking_strategy: balanced
interventions:
  - intervention_id: iv1
    step: 1
    type: inject_news
    payload:
      content: smoke_news
      topic: healthcare
      stance: uncertain
      source_type: official
output:
  output_dir: {output_dir}
  snapshot_each_step: true
  write_decision_trace: true
""",
        encoding="utf-8",
    )

    state = run_single_scenario(config=scenario, emit_summary=False)
    assert state.current_step == 3
    assert len(state.metrics_history) == 3
    assert (output_dir / "final_state.json").exists()
    assert (output_dir / "metrics_history.json").exists()
    assert (output_dir / "explanation_summary.json").exists()

    metrics = json.loads((output_dir / "metrics_history.json").read_text(encoding="utf-8"))
    assert len(metrics) == 3
    assert "discussion_heat" in metrics[-1]
