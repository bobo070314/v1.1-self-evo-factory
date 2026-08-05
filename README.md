# V1.1 Self-Evolving Factory

> 🔄 **V∞ 自进化技能工厂** — 规则引擎驱动 + LLM 闭环优化 + 免疫系统 + Git 版本追踪

[![GitHub repo](https://img.shields.io/badge/repo-bobo070314%2Fv1.1--self--evo--factory-blue)](https://github.com/bobo070314/v1.1-self-evo-factory)
[![Skills](https://img.shields.io/badge/skills-32_live-green)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/skills)
[![Pipeline](https://img.shields.io/badge/pipeline-core%2Fself_evolve-blue)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/core)
[![Gatekeeper](https://img.shields.io/badge/gatekeeper-pre--commit-red)](https://github.com/bobo070314/v1.1-self-evo-factory)
[![Ruff](https://img.shields.io/badge/lint-ruff_0.15.18-purple)](https://github.com/astral-sh/ruff)

---

## 📊 快照（2026-08-05）

| 维度 | 状态 |
|------|------|
| 技能目录总数 | **90** |
| Live 技能 (run.py) | **32** |
| Stub 技能 (SKILL.md) | **58** |
| 自进化闭环 | ✅ SelfEvolver + SelfHealer 双引擎 |
| 免疫系统 (Gatekeeper) | ✅ pre-commit 强制门禁 |
| 全量体检 | ✅ 88 json + 32 py 全绿 |
| Git commits | ✅ 推送 GitHub |

---

## 🧬 核心架构

```
v1.1-self-evo-factory/
├── core/
│   ├── self_evolve.py         # 双引擎：SelfEvolver（评分）+ SelfHealer（自愈+门禁）
│   └── (30+ 核心模块)          # acceptance/ai_acceptance/memory_store...
├── skills/                    # 技能目录
│   └── 90个目录                # 32 live (run.py) + 58 stub
├── scripts/
│   ├── gatekeeper.py          # pre-commit 质量门禁
│   ├── install_hooks.py       # 安装/卸载 gatekeeper hook
│   ├── scan_health.py         # 全技能 _meta.json 体检
│   ├── scan_py_health.py      # 全技能 run.py 语法体检
│   ├── test_self_healing.py   # 自愈闭环演示
│   └── agnes_client.py        # 零成本 agnes-2.5-flash LLM 客户端
├── cn_channels/  config/  tests/  web/
```

## 🔄 免疫系统闭环

```
Linter (诊断) → SelfHealer (证据) → Agnes LLM (修复) → Linter (验证)
      ↑                                                      │
      └────────────── pass? 否 → 回滚 ❌ (不入库)   pass? 是 → ✅
```

**证据驱动，非盲目生成：** 每个文件先由 linter `--json` 出"化验单"
（行号/列号/规则/原因），再把"证据 + 源码"喂给 LLM。这是"手术医生看化验单"，
而不是"算命先生瞎猜"。

## 🚪 The Gatekeeper Protocol（守门人协议）

每次 `git commit` 自动执行质量门禁（由 `install_hooks.py` 注入的
`.git/hooks/pre-commit`）。扫描 `git diff --cached` 的变更文件：

| 判决 | hook 输出 | 你需要做什么 |
|------|-----------|-------------|
| ✅ 体检通过 | `[gatekeeper] ✅ 体检通过: x` | 无需操作，正常提交 |
| 🛠️ 已自愈 | `[gatekeeper] 🛠️ 已自愈: x — 请重新 git add` | 查看文件内容 → `git add x` → 重新 `git commit` |
| ⛔ 拦截 | `[gatekeeper] ⛔ 拦截: x` | **提交被拒**：看报错行号 → 手动修复 → `git add` → `git commit` |

**被拦截了怎么办（化验单解读）：**
1. 看 gatekeeper 输出的 `[Line n, Col m] ERRORTYPE` 行
2. 打开对应文件那一行，修复（缩进/语法/匹配错误等）
3. `git add <file>` → 重新 `git commit`
4. 若自愈成功过（🛠️），先 `git add` 再 commit，别直接 commit

**手动运行门禁（不提交时）：**
```bash
python scripts/gatekeeper.py
```

## 🛠️ Extending the Factory（3 分钟加新 Linter）

给工厂加一种文件类型的"体检能力" = 给 `SelfHealer.VERIFIERS` 加一行映射：

```python
# core/self_evolve.py 里的 SelfHealer.VERIFIERS
VERIFIERS = {
    ".yaml": "skills/yaml-linter/run.py",
    ".yml":  "skills/yaml-linter/run.py",
    ".json": "skills/yaml-linter/run.py",
    ".md":   "skills/markdown-linter/run.py",
    ".css":  "skills/css-minifier/run.py",
    ".py":   None,  # 内置 py_compile 语法校验（无需外部 linter）
}
```

**要求你的 verifier 遵循协议：**
1. 支持 `--json` 输出结构：
   ```json
   {"summary": {"error": 2, "warning": 1},
    "files": [{"file": "x", "error": 2, "warning": 1,
               "diagnostics": [{"status": "error", "line": 5, "column": 1,
                                "reason": "...", "rule": "..."}]}]}
   ```
2. 退出码语义：`0` 健康 / `1` 硬错误 / `2` 仅警告
3. 放在 `skills/<name>/run.py`

加好后，Gatekeeper、SelfHealer、批量扫描将**自动**识别新类型 —— 无需改其他代码。

## 🚀 快速开始

```bash
git clone git@github.com:bobo070314/v1.1-self-evo-factory.git
cd v1.1-self-evo-factory

# 安装免疫门禁（pre-commit hook）
python scripts/install_hooks.py

# 跑自愈闭环演示
python scripts/test_self_healing.py

# CLI 自愈/体检任意文件
python core/self_evolve.py --path some.yaml
python core/self_evolve.py --path some.yaml --no-llm   # 只体检
python core/self_evolve.py --tree skills/ --ext yaml   # 批量

# 全量健康扫描（零 LLM 成本）
python scripts/scan_health.py
python scripts/scan_py_health.py
```

## 🤖 自进化闭环（SelfEvolver）

```
SelfEvolver.evolve() → QualityScorer.score() → FixEngine → 重评分 → KEEP or ROLLBACK
```

- `QualityScorer` 多维评分（语法/安全/风格/完整性/逻辑/性能）
- `< 65 分触发 LLM 修复回调（cloud_fn/llm_chat_fn）
- 分数下降 > 阈值自动回滚
- `gate_path=` 参数让**演化产物过 Gatekeeper 门禁**（不过门禁不算成功）

## 📈 路线图

- [x] V1.1 规则引擎骨架
- [x] V1.2-V2.10 自动闭环 + 技能标准化 + ruff + cron
- [x] 2026-08-05 免疫系统：SelfHealer + Gatekeeper + 健康扫描
- [ ] V3.0 批量复活 58 个 stub
- [ ] V3.1 更多 verifier（ruff/pytest/TS 等覆盖代码质量）

---

<p align="center">
  <sub>Made with 🔥 by OpenClaw International Edition • ASCII art powered by V∞</sub>
</p>
