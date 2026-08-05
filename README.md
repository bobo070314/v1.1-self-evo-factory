# V1.1 Self-Evolving Factory

> 🔄 **V∞ 自进化技能工厂** — 规则引擎驱动 + LLM 闭环优化 + Git 版本追踪

[![GitHub repo](https://img.shields.io/badge/repo-bobo070314%2Fv1.1--self--evo--factory-blue)](https://github.com/bobo070314/v1.1-self-evo-factory)
[![Skills](https://img.shields.io/badge/skills-27_live-green)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/skills)
[![Pipeline](https://img.shields.io/badge/pipeline-core%2Fself_evolve-blue)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/core)
[![Ruff](https://img.shields.io/badge/lint-ruff_0.15.18-purple)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/hook-pre--commit-lightgrey)](https://pre-commit.com/)

---

## 📊 快照（2026-06-23）

| 维度 | 状态 |
|------|------|
| 技能目录总数 | **152** |
| Live 技能 (run.py) | **27** |
| Stub 技能 (SKILL.md) | **95** |
| 第三方源码目录 | **30**（Chart.js / docker / eslint / next.js 等） |
| 自进化闭环 | **27/27 ALL GREEN** |
| Ruff 质量 | **39 fixed, 29 doc-style** |
| Git commits | **10** |
| Cron 每日自愈 | **9:00 Asia/Shanghai** |

---

## 🧬 核心架构

```
v1.1-self-evo-factory/
├── core/
│   ├── self_evolve.py         # 自我迭代闭环引擎 SelfEvolver（评分→修复→回滚）
│   ├── rules_orchestrator.py  # 规则引擎编排
│   └── (30+ 核心模块)          # acceptance/ai_acceptance/memory_store...
├── skills/                    # 技能目录
│   └── 152个目录               # 28 个含 run.py，其余为 SKILL.md stub
├── cn_channels/               # 国内渠道发布（douyin/wechat/xiaohongshu/wecom）
├── config/                    # 配置文件
├── scripts/                   # 演示/工具脚本（demo_phoenix, _evo_smoke...）
├── tests/                     # 测试
└── web/                       # web 界面（chat.py, index.html）
```

## 🔧 技术栈

- **规则引擎**: Pure Python AST + Regex（无外部依赖）
- **代码质量**: Ruff 0.15.18 + Pre-commit hook
- **自愈框架**: self-heal 0.5.0 `@repair` 装饰器
- **Python 版本**: 3.11+
- **Git 仓库**: [bobo070314/v1.1-self-evo-factory](https://github.com/bobo070314/v1.1-self-evo-factory)

## 🚀 快速开始

```bash
# 克隆仓库
git clone git@github.com:bobo070314/v1.1-self-evo-factory.git
cd v1.1-self-evo-factory

# 安装 pre-commit hook
python .git/hooks/pre-commit.py

# 跑自进化闭环
python scripts/run_evo_demo.py   # 或见 core/self_evolve.py 的 SelfEvolver 用法

# 全量质量扫描
python scripts/_evo_smoke.py     # 驱动 SelfEvolver.evolve() 的闭环冒烟测试

# 安装 ruff
pip install ruff
python -m ruff check skills/ --fix
```

## 🤖 自进化闭环

```
SelfEvolver.evolve()  →  QualityScorer.score()  →  FixEngine 修复  →  重评分  →  KEEP or ROLLBACK
```

每次优化都会（见 `core/self_evolve.py`）：
1. `EvolutionLog.start_run()` 记录运行
2. `QualityScorer.score()` 多维评分（语法/安全/风格/完整性/逻辑/性能）
3. `FixEngine` 针对缺陷选择修复策略
4. 低于阈值时调用 LLM 回调（`cloud_fn`/`llm_chat_fn`）自动修复
5. 分数下降超过阈值自动回滚，进化历史存 `data/evolution/`

## 🛡️ 安全审计

`sandbox-executor` 提供 Docker 容器隔离：
- 只读文件系统（read-only root）
- 禁止提权（no-new-privileges）
- 全员能力放弃（cap-drop ALL）
- 默认关闭网络
- 内存限制 + 超时保护

## 📈 路线图

- [x] V1.1 规则引擎骨架
- [x] V1.2 自动闭环（self_improve.py）
- [x] V1.3-V1.4 token-saver + sandbox-executor
- [x] V2.0 12核心技能全部 live
- [x] V2.10 ruff + self-heal-llm + cron 上线
- [ ] V3.0 eval-suite 覆盖率 100%
- [ ] V3.1 notion/linear/wecom 外部 API 集成测试

---

<p align="center">
  <sub>Made with 🔥 by OpenClaw International Edition • ASCII art powered by V∞</sub>
</p>
