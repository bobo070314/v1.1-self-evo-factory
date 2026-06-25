# Coordinator Rules — Natural Language Agent Quality Gates
# ==================================================================
# These rules are loaded at dispatch time. Every agent output MUST pass
# its corresponding check before acceptance. No rubber-stamping.
# ------------------------------------------------------------------
# Format: AGENT_ID -> rule list
# Each rule: natural language description of required quality gate

CSO:
  - CSO输出的PRD必须包含"用户画像"、"竞争分析"、"功能边界"三个章节，缺一打回
  - 用户画像必须包含具体数据（年龄/职业/使用场景），不能用"目标用户群体"这种空泛词
  - 竞争分析必须列出至少2个竞品及其关键差异，不能用"市场上有多个竞品"糊弄
  - 功能边界必须明确写出"不做什么"，不能只列功能清单
  - 输出格式必须用Markdown，标题层级不超过3级

VIS:
  - CSS间距检测：全局gap值必须≥24px（Tailwind gap-6及以上），禁止gap-2/gap-3/gap-4
  - 颜色检测：禁止使用纯黑#000000、pure black，暗色模式主体文字用#e5e5e5
  - 响应式检测：每个组件必须有sm:和md:断点的布局变化，禁止只给一个尺寸
  - 无障碍检测：所有交互元素（button/link/input）必须有focus:ring和键盘可操作
  - 动效检测：transition必须指定具体属性（transition-colors/transition-opacity），禁止transition-all
  - 输出格式：每个组件必须包含完整JSX代码块 + 使用的Tailwind类名清单

CODE:
  - 代码输出前必须过ruff check（Python）或ESLint（JS/TS），报错不交
  - 每个函数必须有类型注解（Python typing）/ TypeScript interface
  - 危险模式拦截：禁止在非隔离环境中执行rm -rf / os.remove("/") / subprocess(shell=True)未过滤输入
  - 文件操作必须用with语句或try-finally，禁止裸open/write
  - 新增依赖必须列出包名+版本+用途注释

OPS:
  - 部署脚本必须先输出dry-run预览，用户确认后才能执行
  - 生产环境操作必须包含回滚方案（不超过3步），无回滚方案直接打回
  - 端口绑定前必须先netstat检查端口占用，禁止硬绑
  - 数据库迁移必须有up和down双向脚本，缺down打回

DOC:
  - 文档必须包含实际可运行的代码示例，禁止伪代码
  - API文档必须包含请求/响应的完整JSON示例
  - 错误处理文档必须列出3种典型失败场景及处理方式
  - 版本号格式必须遵循semver（major.minor.patch）

SEC:
  - 安全审计输出必须包含：漏洞等级/触发条件/修复方案/复现步骤
  - 发现高危（CRITICAL/HIGH）漏洞时，输出第一行必须是"[紧急] 发现高危漏洞"标记
  - 修复方案必须给出至少2种修复方式（快速止血+根治方案）并标注实施难度

GLOBAL:
  - 任何Agent输出中出现"TODO"、"待优化"、"可以考虑"等模糊词，打回要求具体化
  - 任何Agent输出中重复用户的整段话充字数（橡皮图章），打回要求重新输出核心结论
  - 任何Agent输出超过用户输入3倍长度时，必须在开头给出50字以内的TL;DR
