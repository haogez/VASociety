from pathlib import Path

from vasociety.config import load_config


def test_load_yaml_config(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        """
seed: 9
steps: 4
agent_population:
  count: 5
  topics:
    - t1
feed:
  max_items: 6
  view_top_k: 2
output:
  output_dir: outputs/x
interventions: []
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.seed == 9
    assert cfg.feed.view_top_k == 2
    assert cfg.agent_population.topics == ["t1"]


def test_load_json_back_compat(tmp_path: Path) -> None:
    p = tmp_path / "cfg.json"
    p.write_text('{"seed":2,"steps":3,"agent_population":{"count":2},"interventions":[]}', encoding="utf-8")
    cfg = load_config(p)
    assert cfg.steps == 3
    assert cfg.agent_population.count == 2


def test_backward_compat_output_fields(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        '{"seed":1,"steps":2,"output_dir":"outputs/z","snapshot_each_step":false,"interventions":[]}',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert str(cfg.output.output_dir) == "outputs/z"
    assert cfg.output.snapshot_each_step is False
