# VASociety v0.2

VASociety 是一个多智能体互联网舆情仿真与干预推演系统。当前版本 v0.2 在原有可运行骨架上完成了结构化升级：更强类型配置、解耦执行链路、可解释日志、实验型指标与更高测试覆盖。

## 核心架构（v0.2）

- `simulation.engine`: 只负责 step 主循环调度
- `simulation.executor`: 统一动作执行（like/comment/repost/create_post/skip）
- `simulation.recorder`: 快照与结构化行为日志
- `interventions.scheduler` + `interventions.handlers`: 干预调度与落地
- `agents.policy` + `agents.belief`: 感知、belief 更新、决策分离
- `environment.feed_ranker`: 可解释可扩展评分拆解
- `metrics.collector`: 面向实验分析的扩展指标

## 配置格式

- 主配置支持 `.yaml/.yml`（优先）
- 兼容 `.json`
- 若 YAML 解析依赖不可用，仍可读取 JSON 语法配置（向后兼容）

示例配置：`configs/demo.yaml`

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

运行 demo：

```bash
vasociety run --config configs/demo.yaml
```

运行测试：

```bash
pytest -q
```

## 输出文件

默认输出目录：`outputs/demo_run/`

- `final_state.json`
- `metrics_history.json`
- `event_log.jsonl`
- `decision_trace.jsonl`
- `simulation.log`
- `snapshots.json`（可选）

## v0.2 新增指标

- `persona_participation`
- `per_persona_action_distribution`
- `rumor_like_content_count` / `corrective_content_count`
- `rumor_spread_coverage` / `corrective_spread_coverage`
- `stance_shift_count`
- `per_step_topic_heat`

## 后续扩展方向

- 社交关系图谱与 social proximity 真值注入
- 记忆系统与长期 belief 演化
- 平台干预策略（boost/suppress/targeted push）
- 更细粒度可解释实验分析 pipeline
