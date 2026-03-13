import json
from pathlib import Path

from vasociety.cli.main import main


def _write_scenario(path: Path, output_dir: Path, steps: int = 2) -> None:
    path.write_text(
        f"""
scenario_name: cli_case
description: cli integration
topics: [healthcare, economy]
simulation_steps: {steps}
random_seed: 5
initial_population:
  count: 4
  topics: [healthcare, economy]
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
      content: x
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


def test_cli_run_command(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    run_output = tmp_path / "run_output"
    _write_scenario(scenario, run_output, steps=2)

    main(["run", "--config", str(scenario)])

    assert (run_output / "final_state.json").exists()
    assert (run_output / "metrics_history.json").exists()
    metrics = json.loads((run_output / "metrics_history.json").read_text(encoding="utf-8"))
    assert len(metrics) == 2


def test_cli_experiment_and_analyze_commands(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    _write_scenario(scenario, tmp_path / "unused", steps=2)
    exp_output = tmp_path / "exp_output"

    main(
        [
            "experiment",
            "--scenarios",
            str(scenario),
            "--seeds",
            "3",
            "9",
            "--output-dir",
            str(exp_output),
            "--steps",
            "2",
        ]
    )

    summary_path = exp_output / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_runs"] == 2
    assert (exp_output / "run_001" / "final_state.json").exists()
    assert (exp_output / "run_002" / "final_state.json").exists()

    main(["analyze", "--output-dir", str(exp_output / "run_001")])
    report = json.loads((exp_output / "run_001" / "analysis_report.json").read_text(encoding="utf-8"))
    assert report["trace_schema"]["is_valid"] is True


def test_cli_step_mode_supports_runtime_interventions(tmp_path: Path, monkeypatch) -> None:
    scenario = tmp_path / "scenario.yaml"
    run_output = tmp_path / "step_output"
    _write_scenario(scenario, run_output, steps=2)

    commands = iter(
        [
            "add next inject_news '{\"content\":\"manual\",\"topic\":\"healthcare\",\"stance\":\"uncertain\",\"source_type\":\"official\"}'",
            "step",
            "run 1",
            "quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    main(["step", "--config", str(scenario)])

    metrics = json.loads((run_output / "metrics_history.json").read_text(encoding="utf-8"))
    intervention_records = [
        json.loads(line)
        for line in (run_output / "intervention_log.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(metrics) == 2
    assert any(item.get("intervention_id", "").startswith("manual_") for item in intervention_records)
