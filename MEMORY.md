# MEMORY.md
## 2026-06-23 终态 — V2.13 全量快照 (148/148 标准化)

### Git 仓库
- **GitHub**: `git@github.com:bobo070314/v1.1-self-evo-factory.git` (SSH)
- **分支**: master, 23 commits
- **Tag**: v2.13 ✅ 已推送
- **Working tree**: CLEAN ✅
- **.gitignore**: 已修复（覆盖 skills/*/run.py + .deploy/）

### 技能全量分类 — EXTRA DIRS 版（D:\bobo\openclaw-foreign\skills, 148个目录）
- **Live skills (run.py)**: 148 ✅ 全部 v0.2.0 标准化
- **v0.2.0 CLI 标准**: --version / --json / --dry-run 148/148 (100%)
- **Stub skills**: 0
- **Bare**: 1 (qclaw-shared — 共享库，非技能)

### 项目仓库版 (v1.1-self-evo-factory/skills, 152个目录)
- 之前说的 "30 bare" 是 v1.1-self-evo-factory/skills/ 里的第三方源码（Chart.js, docker, eslint等），不是 extraDirs 技能
- 这些 30 bare 目录已被 .gitignore 排除
- 真实的技能全在 extraDirs `D:\bobo\openclaw-foreign\skills` 下

### 自进化闭环
- self_coder.py: 9规则, 0错误, 4假阳性警告
- self_improve.py: V2.10 @repair 集成
- daily_eval_reporter.py: cron 9:00 Asia/Shanghai
- 最终验证: 27/27 ALL GREEN (28.2s)

### V2.11 增补 (2026-06-23 20:20-20:44)
- github-actions-generator v0.2.0 ✅ 5个模板(ci-node/python/go/deploy-pages/schedule) 真实YAML生成
- web-deploy-github v0.2.0 ✅ deploy/status/list/build + gh CLI集成
- git_safe_push.py ✅ 过滤PowerShell stderr误判
- git.cmd wrapper ✅ PATH拦截器 + pathPrepend配置
- report_delivery.py ✅ WeCom/SMTP双通道
- INSTALL.md + setup_new_env.py ✅ 一键部署验证通过
- eval-suite/run_all.py ✅ 主测试入口
- notion v0.2.0 ✅ argparse + --dry-run + Notion API (query/page/create/search)
- linear v0.2.0 ✅ argparse + --dry-run + GraphQL API (issues/create/projects)
- tencent-docs v0.2.0 ✅ argparse + --dry-run + 腾讯文档API (create/list/get)
- wecomcli-msg/contact/doc/meeting/schedule/todo v0.2.0 ✅ 6个技能argparse + --dry-run
- 全量审计: extraDirs 148 live, 0 stub, 1 bare (qclaw-shared)
- ✅ V2.13 终态: 148/148 --version --json --dry-run 全部通过
- ✅ 项目仓库: 25 commits, v2.13 tag 已推送 GitHub

### V3.1 四方向闭环 (2026-06-23 21:42-21:48) — 一次性全交付
- ✅ V3.1: test_api_skills.py — 11/11 API skills dry-run 全部通过
- ✅ V4.0: auth.py — RBAC(5角色: admin/dev/viewer/auditor/operator) + 审计链(hash-linked)
- ✅ Agent: agent_mission.py — Planner→Coordinator→Agents 全链路 3 steps/1.3s/100%
- ✅ Deploy: deploy_full.bat — 7步一键部署, 148 skills全验证
- ✅ 工具链: test_api_skills.py 自动检测11个API技能参数格式并批量验证
- ✅ Commit 6ecd7c2 → 30 commits total, pushed

### V3.0 升级 (2026-06-23 21:33-21:45) — A+B+C+D 全量交付
- ✅ A: pipeline/planner.py — LLM驱动 (DeepSeek API + keyword fallback)
- ✅ A: pipeline/coordinator.py — 并行调度 + DAG拓扑 + @repair重试
- ✅ A: pipeline/agent_registry.py — 5个专业Agent (sec/code/ops/doc/qa)
- ✅ B: pipeline/config_api_tokens.py — Token交互式配置 + 加密存储
- ✅ C: web/dashboard.html — 实时状态监控Dashboard (Agent/技能/日志)
- ✅ D: 5个新技能 — sql-optimizer, api-doc-generator, log-analyzer, config-diff, docker-compose-gen
- ✅ Commit 8580d6a → 28 commits total, pushed

### 基础设施
- ruff 0.15.18: pre-commit hook 已部署 (Python版)
- self-heal 0.5.0: @repair 装饰器已集成
- pyproject.toml: line-length=120, select=E,F,W,I,N,D

### 网络教训
- **SSH > HTTPS**: 本机 HTTPS git push TLS 兼容问题，SSH 直通 GitHub ✅
- 代理 127.0.0.1:7890 存活但 git HTTPS 不走 socks5
- gh CLI 已登录 bobo070314，用 gh repo create 建仓库

## 已知的项目路径
- 主站项目：D:\bobo\openclaw-foreign\workspace\gh-enterprise-baseline\
- 工具脚本：D:\bobo\openclaw-foreign\workspace\scripts\
- Git 仓库：D:\bobo\openclaw-foreign\.git
- OpenClaw 配置：D:\bobo\openclaw-foreign\openclaw.json

## 踩过的坑（别再犯）
- **extraDirs 技能必须加 YAML frontmatter**，否则 OpenClaw 不编译进 system prompt，AI 无法感知
- **extraDirs 技能必须在 skills.entries 中显式 enabled: true**，光有 frontmatter 不够，OpenClaw 需要 entries 声明才会注入
- **OpenClaw 不是 function calling 调度** extraDirs 技能，而是编译 SKILL.md 为 XML 注入 system prompt，AI 自主调用 exec
- node 版本要用 18+，16会炸
- npm run build 前要删 .next/cache 否则偶尔 OOM
- Windows 下路径要用反斜杠或双反斜杠
- npm install 前先清理 package-lock.json 避免版本冲突
- **Windows 下 python3 命令不存在，用 python 替代**（github-ai-trends 等技能 SKILL.md 写的是 python3）
- **PYTHONIOENCODING=utf-8 需设置**，否则 Windows GBK 终端会炸 emoji/unicode 输出
- **PowerShell 下 Python inline -c 会吃引号** → 走 .py 文件执行，不要 inline 复杂的多行代码
- **GitHub Token 未配时限速 10 req/min**，配了才能正常用 github-ai-trends / read-github
- **npx 在 Windows 上包嵌套太深会报错"此时不应有 )"**，优先用 openclaw skills install 直装
- **QClaw 的 openclaw.cmd 劫持 CLI**，国际版要用 `C:\Users\asus\AppData\Roaming\npm\openclaw`
- **Gateway 热重启有概率闪退**，优先冷启动：kill 进程 → 等 2s → 重新 `start`
- **winget 缓存锁在 D:\bobo\Temp**，文件被占用时安装失败，改用 Python 原生替代方案
- **os.walk 遍历 D 盘 → 必 OOM**，2TB 文件系统不能用 walk，用已知路径列表
- **Git push exit code 1 是 PowerShell 误判**，git 所有输出走 stderr，PowerShell 把非空 stderr 当错误
- **修复方案：scripts/git_safe_push.py**，判断 fatal/error/Permission denied 等真失败才 non-zero
- **Gateway 里需用 `python scripts/git_safe_push.py` 替代 `git push` 避免持久报错**
- **process tool session 被 kill 后查不到 log**，直接 `process list` 看状态即可，别反复 poll

## 偏好
- 样式用 Tailwind，不用 CSS Module
- 组件放 src/components/，页面放 src/pages/
- 代码格式化用 Prettier + ESLint
- Git 提交信息用中文，技术术语保留英文

## 技能矩阵（2026-06-22 终态）
### 核心安装（14）
- Tier 1 基础：tavily-search, nano-pdf, summarize, weather
- Tier 2 开发/GitHub：github, read-github, github-ai-trends, agent-browser, web-scraper, code-runner, github-actions-generator, web-deploy-github
- Tier 3 记忆/学习：self-improving-agent, skill-vetter, ontology

### 自制技能（3）
- site-doctor（网站健康诊断）
- reasoning-framework（推理规划框架，封装 Sequential Thinking MCP）
- model-selection-rules（模型选择与降级策略）

### extraDirs 技能（63，其中 6 个 v0.2.0 implemented）
- ✅ **create-skill** v0.2.0 — 技能工厂，Context Snapshot 自举
- ✅ **agent-testing** v0.2.0 — 多框架测试运行器（pytest/vitest/jest/cargo/go）
- ✅ **db-migrations** v0.2.0 — Prisma 迁移脚本（跨平台 Python）
- ✅ **add-setting-env** v0.2.0 — 环境变量验证器（.env vs .env.example）
- ✅ **code-navigator** v0.2.0 — 符号级代码导航（函数/类/接口/导出/导入 + 模糊搜索）
- ✅ **frontend-code-review** v0.2.0 — ESLint 增强审查（符号交叉引用 + 修复建议 + 质量评分）
- 其余 57 个 stub（SKILL.md frontmatter + _meta.json + run.sh 就绪，待实现）

### 从 gh-enterprise-baseline 包装（4）
- n8n-db-migrations（数据库迁移规范，46KB）
- n8n-code-review（Code Review 规范，10KB）
- lobe-agent-testing（Agent 端到端测试框架，20KB）
- lobe-data-fetching（前端数据获取架构，18KB）

---

## 2026-06-23 今日战果 — V∞ 自进化工厂首批技能

### 新增/升级技能（5个）
- ✅ **security-audit** v0.2.0 — 静态代码安全审计器（9条规则，AST+正则，SQL注入/XSS/硬编码密钥/命令注入/路径穿越）
- ✅ **drizzle** v0.2.0 — drizzle-kit wrapper（--dry-run + --json + 错误处理）
- ✅ **token-saver** v0.1.0 — 命令输出智能压缩器（200行→36行，82%压缩率，subprocess utf-8全覆盖）
- ✅ **exec-wrapper.py** — token-saver透明代理，挂载到主执行链
- ✅ **sandbox-executor** v0.3.0 — Docker容器隔离 + 原生回退，统一入口

### eval-suite 评测闭环（10/10 100分）
- ✅ test_case_01_sql_injection.py → security-audit → 100/100
- ✅ test_drizzle.py → drizzle --dry-run + JSON → 100/100
- ✅ test_release_notes.py → release-notes-generator → 100/100
- ✅ test_code_navigator.py → code-navigator → 100/100
- ✅ test_deployment.py → deployment-automation (deploy/rollback/health) → 100/100
- ✅ test_create_pr.py → create-pr (no-token graceful) → 100/100
- ✅ test_db_migrations.py → db-migrations (dry-run/status) → 100/100
- ✅ test_infra_diagram.py → infra-diagram-as-code (Mermaid/JSON) → 100/100
- ✅ test_token_saver.py → token-saver (exit code passthrough) → 100/100
- ✅ test_sandbox.py → sandbox-executor (Docker isolation + host file intact) → 100/100
- 📁 run_all.py → 一键批量运行，5.6s 全绿

### Windows 系统坑修复（全技能覆盖）
- `subprocess.run(text=True)` 默认 GBK → 统一加 `encoding="utf-8", errors="replace"`
- `datetime.UTC` 3.11+ only → `timezone.utc` 兼容写法
- PowerShell 下 `python -c` 吃引号 → 一律走 .py 文件
- `findstr` 不支持 `\*\` glob → 用 Python Path.glob 替代

### 未完成
- 扩展 eval-suite 覆盖剩余技能（notion/linear/wecomcli 等需外部 API）


### 2026-06-23 深夜 — self-coder 规则引擎闭环
- ✅ self-coder v0.2.0 — --rules 模式，Pure Python 规则引擎，无需 API Key
- ✅ self_improve.py — 一键闭环：优化→eval→apply→re-eval→keep/rollback
- ✅ eval-suite: 11/11 ALL PASSED, 5.9s
- ✅ V∞ HEALTH: 5/5 PASS
- ✅ 全技能 146/149 有用 run.py
- ⏳ 唯一缺口：notion/linear/wecomcli 等需要外部 API 的测试
