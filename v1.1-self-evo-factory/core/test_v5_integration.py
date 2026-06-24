"""验证 V5.0 五层全通报告"""

import json
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "pipeline/agent_mission_v5.py", "--demo", "--goal", "审计代码安全", "--json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory",
    timeout=30,
)

output = result.stdout.strip()
d = json.loads(output)

checks = []
checks.append(
    (
        "报告包含5+顶级key",
        len(
            [
                k
                for k in ["memory", "plan", "execution", "coordinator", "safety", "cost", "kairos", "anti_distillation"]
                if k in d
            ]
        )
        >= 5,
    )
)
checks.append(("cost字段存在", "cost" in d))
checks.append(("kairos字段存在", "kairos" in d))
checks.append(("anti_distillation字段存在", "anti_distillation" in d))
checks.append(("缓存报告", "cache" in d.get("cost", {})))
checks.append(("API报告", "api" in d.get("cost", {})))
checks.append(("预算状态", "budget" in d.get("cost", {})))
checks.append(("Kairos任务>=5", len(d.get("kairos", {}).get("tasks", [])) >= 5))
checks.append(("反蒸馏环境OK", d.get("anti_distillation", {}).get("environment_ok", False)))

passed = sum(1 for _, ok in checks if ok)
total = len(checks)

for name, ok in checks:
    print(f"  {'✅' if ok else '❌'} {name}")

print(f"\n{'=' * 40}")
print(f"  {passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
