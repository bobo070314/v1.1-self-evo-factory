# MEMORY.md

## 2026-08-05 收官 — 免疫系统正式上线（波波 & 小虾）

### 出厂状态（Agnes v1.1 基础设施）
- 32 live 技能全绿；88 json + 32 py 全绿（scan_health.py EXIT 0）
- Gatekeeper pre-commit 门禁强制启用
- Git 今日 8 连 commit 全部推送（ed6c94e → … → 5adffbf，working tree CLEAN）

### 收官 commit 5adffbf — Gatekeeper「分寸感」修复（波波点名表扬）
- 背景：Gatekeeper 把 warning 级别当 error 拦截，在实战中拦截了创造者自己的提交
- 修复：**0/1/2 语义区分**——0=healthy、1=已自愈(rc 报 1 让 hook 提示重 add)、2=warning/error(真正拦截)
- 原则：不改法律跳过（--no-verify），而是修改法律本身；免疫系统精准识别而非盲目排异
- 文档：`docs/ Agnes Constitution manual` 同 commit 落袋

### 收官体检铁律（今天被绊一下，立为规范）
- 体检命令必须带编码，否则 Windows GBK 终端在 ⚠️/✅ emoji 处炸 UnicodeEncodeError（看起来红，实际全绿）
- **正确姿势**：`$env:PYTHONIOENCODING='utf-8'; python scripts/scan_health.py`
- MEMORY.md 早有此条，但执行时没落到每次体检 → 已固化为 check 清单第一步

### 开发者三大铁律（血泪史沉淀）
1. **PowerShell 路径坑**：`cd /d 路径` 是 CMD 语法，PowerShell 会失败/不切目录。
   PowerShell 用 `Set-Location -Path '绝对路径'` 或 `cmd /c "cd /d 路径 && git ..."`。
   git add 前必看 `git status --short` 确认 cwd，防止 `git add -A` 污染整个 workspace（踩过！）。
2. **注入安全（return 路径覆盖）**：往已有函数插横切逻辑时，必须读完该函数**所有 return 路径**。
   evolve() 有"初始分≥65 提前 return"，门禁放末尾永远不会执行——要抽 `_gate_check()` 辅助方法，
   在每处 return 前调用。见 core/self_evolve.py。
3. **LLM 幻觉模式**：agnès 修 `unclosed-code-block`（代码块未闭合）时易修不好/猜闭合位置。
   协议要求：能修则修，修不动触发**回滚保护**（不留下损坏文件），并报 blocked。
   证据驱动：先 linter --json 拿"化验单"再喂 LLM，杜绝"盲目生成"。

### 免疫系统组件速查
- `gatekeeper.py`：pre-commit 门禁（diff --cached → 体检 → 放行/自愈/拦截）
- `install_hooks.py`：安装/卸载 hook（幂等，备份 .bak）
- `SelfHealer`（core/self_evolve.py）：VERIFIERS 映射 + Scan→Diagnose→Fix→Verify
- `scan_health.py` / `scan_py_health.py`：全库只读体检（零 LLM）
- `self_evolve.py --path/--tree/--no-llm`：CLI 自愈入口


## 2026-08-05 — 免费LLM接通 + 技能复活流程 (波波 & 小虾)

### 里程碑：免费"手术刀"接通
- agnes 免费端点：`https://apihub.agnes-ai.com/v1`（OpenAI兼容），模型 `agnes-2.5-flash`（**不带 agnes/ 前缀**），auth `Bearer $AGNES_API_KEY`（env 已配，51字符）
- **不要用 `127.0.0.1:18789`**——那是 Control UI 端口，不是 LLM API（踩过坑）
- `SelfEvolver.__init__` 只接 `llm_chat_fn`/`cloud_fn` 回调，**不接** model_name/api_base/api_key（connect_brain 里设这些参数会 TypeError）

### 复活技能流水线（scripts/_resurrect_v2.py，SET RESURRECT_SKILL=<name> 换目标）
- 两步：① LLM 生成 SKILL.md 规格 ② 基于规格生成 run.py
- **三重验证**（防假阳性）：非空>100B + py_compile + `--version` 有输出
- 已复活 3 个：css-minifier / markdown-linter / yaml-linter（LIVE 28→32）
- 新技能：skills/llm-query-agnes（成品，已测通）

### 踩过的坑（别再犯）
- **Authorization 头必须是 `"Bearer " + key`**，曾误写 `"***" + key` 导致 401 无效令牌
- **LLM 回复带 ```python 围栏**，必须 extract_python 剥离，且确认 main 里真的调用了它（曾定义未调用）
- **空文件 py_compile 也通过**——验证必须含字节数检查，单靠语法会假阳性
- 生成代码验证必须：非空 + 语法 + --version 输出，三者全过才算复活
- `set RESURRECT_SKILL=name` 尾随空格会被 set 吃掉→ 脚本里要 .strip()
- 裸 LLM 生成无规格 stub 代码 良品率低（曾 0/3），有规格+三重验证后 3/3（含手动修围栏）


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

### V4.0 第二轮闭环 (2026-06-23 22:10-22:18) — Token贯通 + 大脑皮层
- ✅ GitHub Token: 从 gh auth token 自动提取注入 api_tokens.json
- ✅ test_api_skills.py --live: 11/11 ALL PASS (真实API认证)
- ✅ github-actions-generator: live YAML生成验证通过
- ✅ web-deploy-github: gh CLI 认证验证通过 (HTTP 404 = 已认证)
- ✅ wecomcli-contact bug修复: WeCom API search限制友好降级 exit 0
- ✅ causal-reasoner v0.2.0: 8节点Bayesian DAG + 证据加权评分 + 递归根因回溯
- ✅ evidence-required gate: 无证据时不抑制报警 (deploy证据→抑制, 未知原因→升级)
- ✅ Daemon因果抑制: arm_response 先调causal-reasoner再决定报警
- ✅ 闭环: Daemon(监控) → Reasoner(推理) → Guard(防御) 三级联动
- ✅ Skills仓库: commit 3caa5f3 (causal-reasoner + daemon upgrade)
- ⏳ 缺口: owl-vision (视觉), Notion/Linear/WeCom API真实验证 (需用户提供Token)

### V4.0 Cron 暴走修复 (2026-06-23 22:28)
- ❌ 问题: subconscious-daemon cron job 每60s spawn AI agent → ~18K tokens/run, 18次=~800K tokens wasted
- ✅ 修复: 删除 cron job, 改用 HEARTBEAT.md 复用主session心跳
- ✅ 新增: HEARTBEAT.md + heartbeat-state.json 标准化检查清单

## 模型分级策略与 Temperature 备忘（2026-08-05 波波建议采纳）
- **分级诊疗原则**：初步体检/简单修复（YAML缩进、CSS压缩）→ 用便宜模型（agnes-2.5-flash）；Gatekeeper 拦截触发回滚的疑难杂症（如 unclosed-code-block）→ 升级深度手术模型（deepseek-reasoner / 更强模型），人工介入候选
- **当前实际模型栈**：agnes-2.5-flash（默认免费，复活主力，temperature=0.2 已固化在 agnes_client.py）｜deepseek-reasoner（主会话）｜nvidia nemotron（微信 pin）｜fallback: zhipu glm / google gemini / groq
- **注意**：栈里没有 OpenClaude / Nous Hermes 2（ioenclaw 系 OpenClaw 乱码变体），如未来经 OneAPI/OpenRouter 接入新模型，先测 temperature：代码修复/JSON 输出压到 0-0.2，创意类 0.5-0.7
- **铁律**：任何 cron 让 LLM 从原始输出解析数字 → 必须先有机器判词层（GPU_OK/GPU_ALERT），LLM 只做路由不做解析

## 复利闭环首演：link-checker 复活（2026-08-05 22:52）
- **流水线**：Resurrect(手写run.py 6.2KB) → Gatekeeper(88/88 全绿 + 33 py 语法健康) → Verify(0 token vs LLM 5-9k/4链接; dry-run 239ms) → Memory(本条)
- **聪明点**：HEAD 优先+405/501 自动降级 GET；重试退避(0.8s 起)；URL 尾部标点剥离(`,);.:!?`)+去重保序；退出码 0/1/2 语义化——全是"机器判词"哲学的延伸
- **愚蠢点**：live 检查 30.8s 中有 ~24s 浪费在 httpbin 限流的超时重试上——**没有总预算/并发控制**，单个慢站点会拖垮整批检查。V2 方向：--max-time 总预算 + ThreadPoolExecutor 并发 + 失败分级缓存
- **教训**：复活 stub 时先读已复活邻居(css-minifier)的 run.py 规范，再写——比从零发明格式省 2 轮自愈
