# core/ — 猫抓工业级内核 V5.0

对标 Claude Code 的五层架构，59 项测试全部通过。

## 架构分层

```
core/
├── memory/          🧠 记忆系统 — 对标 Claude Code 4 类记忆
│   ├── memory_types.py     4 类记忆定义 + JSON 持久化存储
│   ├── memory_index.py     TF-IDF 倒排索引（中文 n-gram 分词）
│   ├── memory_retriever.py 小模型检索员（意图分析→索引检索→格式化上下文）
│   └── memory_extractor.py 后台静默提取（正则规则自动分类入库）
│
├── coordinator/     🤖 Coordinator 模式 — AI 项目经理
│   ├── coordinator_agent.py     任务拆解/分配/验收/重试（拒绝橡皮图章）
│   ├── acceptance_criteria.py   验收标准引擎（5 种任务类型模板）
│   └── natural_commands.py      自然语言→ParsedCommand 解析器
│
├── security/        🛡️ 安全系统 — 23 道检测 + YOLO 分类器
│   ├── safety_checker.py   23 道规则（注入/破坏/泄漏/网络/混淆）
│   ├── yolo_classifier.py  6 级决策分类器（ALLOW→SANDBOX→ASK→BLOCK）
│   └── operation_log.py    Hash 链操作日志（防篡改+可追溯）
│
├── cost/            💰 省钱模式 — 缓存追踪 + 成本追踪
│   ├── cache_manager.py       14 种缓存失败原因追踪
│   ├── api_cost_tracker.py    多维度成本统计 + 预算告警
│   └── dangerous_prompts.py   8 个"改了就炸缓存"危险区域标注
│
├── secrets/         🔮 秘密武器 — Kairos 7x24h + 反蒸馏
│   ├── kairos_scheduler.py    7 个预置定时任务（cron/interval 双模式）
│   └── anti_distillation.py   4 层环境验证 + 水印注入 + 陷阱激活
│
├── test_core.py     ✅ 59/59 单元测试
└── test_v5_integration.py  ✅ 9/9 集成测试
```

## 执行入口

```bash
# 五层全通执行
python pipeline/agent_mission_v5.py --goal "审计代码安全并部署"

# 仅预览（不实际执行）
python pipeline/agent_mission_v5.py --goal "写一个登录模块" --dry-run --strict

# 查看各子系统状态
python pipeline/agent_mission_v5.py --memory-stats
python pipeline/agent_mission_v5.py --safety-stats
python pipeline/agent_mission_v5.py --cost-stats
python pipeline/agent_mission_v5.py --kairos-stats

# 运行全部测试
python core/test_core.py
python core/test_v5_integration.py
```

## 执行流程

```
用户命令
  → 1. 记忆检索（4 类记忆 + TF-IDF 索引）
  → 2. 命令解析（自然语言→action/priority/evidence）
  → 3. Coordinator 拆解（复合任务识别 + 验收标准生成）
  → 4. YOLO 安全检查（23 道检测 + 6 级分类）
  → 5. 执行 + 验收（拒绝橡皮图章 + Hash 链日志）
  → 6. 记忆提取（静默学习）+ 成本追踪
  → 五层完整报告
```

## 设计原则

1. **零外部依赖**：TF-IDF 不依赖向量库，规则引擎不依赖 LLM
2. **分层可测**：每层独立 import、独立 test、独立替换
3. **管道贯通**：五层数据在 `agent_mission_v5.py` 中一条 pipeline 贯通
4. **对标 Claude Code**：每个模块都有对应的 Claude Code 概念映射
