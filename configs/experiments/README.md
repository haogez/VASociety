# Experiment Configs

`vasociety experiment` 支持读取实验配置文件。示例见 `demo_experiment.yaml`。

字段说明：

- `name`: 实验名（可选）
- `output_dir`: 实验输出目录
- `scenarios`: 场景配置路径列表（相对路径相对于本文件）
- `seeds`: 随机种子列表
- `steps`: 覆盖场景中的仿真步数（可选）
- `snapshot_each_step`: 是否每步保存快照
- `write_decision_trace`: 是否输出 `decision_trace.jsonl`
