# core/coordinator/ — AI项目经理 + 自然语言命令 + 拒绝橡皮图章
# 对标 Claude Code 的 Coordinator 模式

from .coordinator_agent import CoordinatorAgent, VerificationLevel, Task, TaskStatus, Mission
from .acceptance_criteria import AcceptanceCriteria
from .natural_commands import NaturalCommandParser
