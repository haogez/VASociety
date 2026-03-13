# VASociety v0.2 (vNext Baseline)

VASociety 是一个面向“社会仿真 + 干预实验 + 可解释追溯”的轻量多智能体框架。  
当前版本聚焦 Python 3.11+ 的可运行、可测试、可扩展工程基线。

## 项目定位

- 从单一 demo 演进为 scenario-driven 仿真框架
- 支持规则推荐、社会关系、平台治理干预、结构化追溯日志
- 输出面向实验分析（而不是只做调试日志）

## 架构（文字图）

- `config`: YAML-first 场景配置与旧 demo 配置迁移
- `simulation.engine`: 纯编排层（intervention/env/online/feed/policy/executor/metrics/record）
- `simulation.executor`: 动作校验、执行、效果发射
- `interventions`: `scheduler`（何时触发） + `handlers/governance`（如何改状态）
- `environment`: 可见性、内容池、热度衰减、feed ranking
- `analytics`: `trace_analyzer` + `explain`，生成可分析实验产物
- `io.save/io.load`: 结构化输出与兼容加载

## 配置体系

推荐使用：

- `configs/scenarios/*.yaml`
- `configs/populations/*.yaml`
- `configs/platforms/*.yaml`
- `configs/experiments/*.yaml`

默认 demo 场景：`configs/scenarios/demo.yaml`

## CLI

安装后命令为 `vasociety`（或 `python -m vasociety.cli.main`）。

### 1) run

运行单个场景：

```bash
vasociety run --config configs/scenarios/demo.yaml
```

常用参数：

- `--output-dir`
- `--seed`
- `--steps`
- `--snapshot-each-step / --no-snapshot-each-step`
- `--write-decision-trace / --no-write-decision-trace`

兼容写法（默认按 run 处理）：

```bash
vasociety --config configs/scenarios/demo.yaml
```

### 2) experiment

两种方式：

1. 直接传场景与种子：

```bash
vasociety experiment \
  --scenarios configs/scenarios/demo.yaml \
  --seeds 7 11 \
  --output-dir outputs/experiments/exp_cli \
  --steps 6
```

2. 读取实验配置文件：

```bash
vasociety experiment --experiment-config configs/experiments/demo_experiment.yaml
```

会在实验目录下生成 `run_001/`, `run_002/`, ... 与 `summary.json`。

### 3) analyze

对某个 run 输出目录做分析汇总：

```bash
vasociety analyze --output-dir outputs/demo_run
```

输出 `analysis_report.json`（并复用已有结构化日志/分析文件）。

## 输出文件说明

单次 run 目录（例如 `outputs/demo_run/`）包含：

- 运行状态：
  - `world_state.json`
  - `run_artifacts.json`
  - `final_state.json`（`final_state.v2`，摘要优先）
- 指标：
  - `metrics_history.json`
  - `metrics_log.jsonl`
- 追溯日志：
  - `event_log.jsonl`
  - `perception_log.jsonl`
  - `decision_log.jsonl`
  - `execution_log.jsonl`
  - `intervention_log.jsonl`
  - `decision_trace.jsonl`
- 分析产物：
  - `trace_analysis.json`
  - `explanation_summary.json`
  - `analysis_report.json`（执行 analyze 后）
- 其他：
  - `snapshots.json`（开启快照时）
  - `simulation.log`

## 测试

```bash
pytest -q
```

当前测试组织：

- 模块测试：`tests/test_*.py`
- 集成测试：`tests/integration/`
- 场景 smoke：`tests/scenario/`

最小 smoke 测试覆盖：

- 从 scenario 启动
- 生成输出文件
- 汇总 metrics 可读

## 迁移说明：旧 demo 配置 -> 新 scenario 配置

仍兼容旧字段（加载时自动迁移），核心映射如下：

- `seed` -> `simulation.random_seed`
- `steps` -> `simulation.simulation_steps`
- `agent_population` -> `initial_population`
- `feed` -> `platform_rules.feed`
- `output_dir/snapshot_each_step/write_decision_trace` -> `output.*`

建议逐步迁移到新格式，避免后续实验配置重复维护两套语义。
