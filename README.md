# VASociety (Phase 1)

VASociety 是一个多智能体互联网舆情仿真与干预推演系统。本仓库当前交付第一阶段：可运行、可测试、可扩展的后端仿真骨架。

## 技术选型

- Python 3.11+
- 数据模型：`dataclasses`
  - 选择原因：第一阶段核心是轻量工程骨架与可演进模块边界，`dataclasses`依赖少、序列化方便、与类型注解配合良好。
- CLI：`argparse`
- 配置：JSON 语法配置文件（示例文件名为 `demo.yaml`，便于后续切换为 YAML）
- 测试：`pytest`

## 目录结构

```text
VASociety/
  README.md
  pyproject.toml
  requirements.txt
  .gitignore
  configs/
    demo.yaml
  src/
    vasociety/
      __init__.py
      config.py
      logger.py
      types.py
      models/
      agents/
      environment/
      simulation/
      interventions/
      metrics/
      io/
      cli/
  tests/
```

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
pytest
```

## 第一阶段能力

- Step-based 仿真主循环
- 简化社交平台与内容热度衰减
- 独立 feed ranking 模块（可替换）
- 规则驱动 agent 决策（无 LLM）
- 干预机制：`inject_news` / `inject_fact_check`
- 指标统计与输出：
  - `final_state.json`
  - `metrics_history.json`
  - `event_log.jsonl`
  - `simulation.log`
  - 可选 `snapshots.json`
