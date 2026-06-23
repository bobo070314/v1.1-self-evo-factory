# V3.0 多 Agent 协作架构 — "单人天花板"突破计划

> 从 V2.13 起步：148 个技能标准化，24 commits，全量 CLI 统一。
> 目标：从单 Agent 执行升级为多 Agent 自主规划与协作。

---

## 1. 架构总览

```
用户指令
  │
  ▼
┌──────────────┐
│  Planner     │  ← 自然语言 → DAG (有向无环图)
│  (规划器)     │     规则引擎 + LLM 推理
└──────┬───────┘
       │ Step[]
       ▼
┌──────────────┐
│ Coordinator  │  ← 调度执行、收集结果、重试
│  (协调器)     │     @repair 全路径守护
└──────┬───────┘
       │ 路由到专业 Agent
       ▼
┌────────────────────────────────────────┐
│         Agent Registry (注册表)          │
│                                         │
│  ┌──────────┐ ┌─────────┐ ┌─────────┐ │
│  │sec-agent │ │code-agent│ │ops-agent│ │
│  │12 rules  │ │navigate │ │deploy   │ │
│  │audit     │ │review   │ │rollback │ │
│  └──────────┘ └─────────┘ └─────────┘ │
│        工具库 = 148 标准化技能          │
└────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Message Bus  │  ← Agent 间通信
│  (消息总线)   │     celery/Redis/本地队列
└──────────────┘
```

---

## 2. 核心组件

### Planner（规划器）
- **输入**：用户自然语言目标
- **输出**：`Step[]` — 有序步骤 DAG（含依赖关系）
- **V3.0-alpha 策略**：规则匹配（关键词 → 技能映射）
- **V3.0-beta 策略**：LLM 推理（few-shot prompt + 结构化输出）
- **落地文件**：`pipeline/planner.py`

### Coordinator（协调器）
- **输入**：Planner 的 Step[]
- **职责**：
  1. 拓扑排序 → 执行顺序
  2. 逐个调用技能 `run.py`
  3. 收集结构化输出（JSON）
  4. 失败时 @repair 守护
  5. 汇总结果给用户
- **落地文件**：`pipeline/coordinator.py`

### Agent Registry（注册表）
- 当前 148 个技能 = Agent 工具库
- 每个技能映射到至少一个 Agent
- 新增技能 → 自动注册（`_meta.json` 解析）

### Message Bus（消息总线）
- V3.0-alpha：本地 subprocess 调用（同步）
- V3.0-beta：文件队列（`state/queue/`）
- V3.0-rc：celery + Redis

---

## 3. 里程碑

| 版本 | 目标 | 验收标准 |
|------|------|----------|
| **V3.0-alpha** | Planner 原型 | 输入 "部署并审计" → 输出 2步DAG |
| **V3.0-beta** | Coordinator 调度 | 执行 multi-step 并汇总结果 |
| **V3.0-rc** | 2 Agent 协同 | sec-agent + code-agent 并行执行 |
| **V3.0** | 产物发布 | GitHub Release + demo video |

---

## 4. 与 V2.13 的关系

- V2.13 = 原子能力（148 个技能，标准化 CLI）
- V3.0 = 编排能力（把这些技能串成流水线）
- 不替换 V2.13 → V2.13 是 V3.0 的 tool layer

---

## 5. 风险评估

| 风险 | 应对 |
|------|------|
| Planner 误拆解 | 规则引擎优先 → LLM 兜底，结果可审计 |
| Agent 间通信延迟 | V3-alpha 用同步调用，beta 再异步 |
| 技能不可用 | Coordinator 检测 `--json` output → 降级 |
