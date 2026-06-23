#!/usr/bin/env python3
"""猫抓 GitHub Predator (开源吞噬者)
自主狩猎 GitHub 上的优质代码，消化吸收，强壮自身。
每天自动扫描，找新鲜养分，咀嚼融合，有毒就吐。
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(os.environ.get("PREDATOR_BASE", "D:/bobo/openclaw-foreign/workspace"))
STATE_FILE = BASE / ".deploy" / "predator_state.json"
NUTRIENTS_FILE = BASE / "core" / "external_nutrients.py"
QUARANTINE_DIR = BASE / ".deploy" / "quarantine"

# 猎物签名：哪些代码模式值得吸收
HIGH_VALUE_SIGNATURES = [
    r"def\s+evolve\b",
    r"def\s+self\s*[-_]\s*heal\b",
    r"def\s+causal\s*[-_]\s*reason\b",
    r"def\s+rollback\b",
    r"def\s+auto\s*[-_]\s*fix\b",
    r"def\s+anomaly\s*[-_]\s*detect\b",
    r"circuit\s*[-_\s]*breaker",  # lowered: matches class/def/var
    r"def\s+balanc\w+\s*[-_]\s*monitor\b",
    r"def\s+resilien\w+\b",
    r"def\s+fault\s*[-_]\s*toler\w+\b",
    r"class\s+\w*Heal\w*\b",
    r"class\s+\w*Guard\w*\b",
    r"class\s+\w*Circuit\w*[Bb]reaker\w*\b",
    r"def\s+backoff\b",
    r"def\s+retry\b",
    r"def\s+fallback\b",
    r"def\s+recover\w*\b",
    r"class\s+\w*Retry\w*\b",
    r"class\s+\w*Resilien\w+\b",
    r"class\s+\w*Fallback\w*\b",
]

# 毒物签名：绝对不能吞的代码模式
POISON_SIGNATURES = [
    r"os\.system\s*\(",
    r"subprocess\.run\s*\([^)]*shell\s*=\s*True",
    r"__import__\s*\(\s*['\"]os['\"]",
    r"eval\s*\(\s*__",
    r"exec\s*\(\s*__",
    r"base64\.b64decode",
    r"requests\.(get|post)\s*\(\s*['\"](?!https?://api\.)",
    r"shutil\.rmtree\s*\(\s*['\"/]",
    r"pickle\.loads",
]


def ts():
    return datetime.now(timezone.utc).isoformat()


def is_poison(code_snippet: str) -> bool:
    """毒物检测：吞之前先闻一下"""
    for pat in POISON_SIGNATURES:
        if re.search(pat, code_snippet, re.IGNORECASE):
            return True
    return False


def extract_nutrient_name(code: str) -> str:
    """从代码里提取一个人类可读的营养名"""
    m = re.search(r"def\s+(\w+)", code)
    if m:
        return m.group(1)
    m = re.search(r"class\s+(\w+)", code)
    if m:
        return m.group(1)
    return "unknown_nutrient"


def score_nutrient(code: str) -> int:
    """给代码块打分：命中签名越多越有价值"""
    score = 0
    for pat in HIGH_VALUE_SIGNATURES:
        if re.search(pat, code, re.IGNORECASE):
            score += 10
    return score


class GitHubPredator:
    """开源吞噬者：嗅探 → 捕获 → 咀嚼 → 融合 → 代谢"""

    def __init__(self):
        self.headers = {}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.load_state()

    def load_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            self.state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        else:
            self.state = {"last_hunt": "", "consumed": [], "quarantined": [], "nutrients": {}}
        self.state.setdefault("consumed", [])
        self.state.setdefault("quarantined", [])
        self.state.setdefault("nutrients", {})

    def save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def hunt_fresh_meat(self):
        """主狩猎逻辑：从 GitHub 搜新鲜 Python 仓库"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state["last_hunt"] == today and not daily:
            print(f"[Predator] 今天已进食，跳过 ({today})")
            return []

        print("[Predator] 出发狩猎新鲜代码...")
        since = (datetime.now() - timedelta(days=7)).isoformat()

        queries = [
            f"language:Python created:>{since} topic:automation stars:>3",
            f"language:Python created:>{since} topic:self-healing stars:>3",
            f"language:Python created:>{since} topic:fault-tolerance stars:>3",
        ]

        import urllib.parse

        all_repos = []
        for q in queries:
            url = (
                f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=3"
            )
            try:
                resp_data = self._api_get(url)
                all_repos.extend(resp_data.get("items", []))
            except Exception as e:
                print(f"[Predator] 搜索失败 ({q[:40]}...): {e}")

        # 去重
        seen = {r["full_name"] for r in self.state["consumed"]}
        fresh = [r for r in all_repos if r["full_name"] not in seen]

        print(f"[Predator] 发现 {len(all_repos)} 个仓库，{len(fresh)} 个新猎物")

        results = []
        for repo in fresh[:5]:  # 每轮最多消化5个
            print(f" -> 猎物: {repo['full_name']} ({repo.get('stargazers_count', 0)} stars)")
            consumed = self.consume_repo(repo)
            results.extend(consumed)

        self.state["last_hunt"] = today
        self.save_state()
        return results

    def _api_get(self, url: str) -> dict:
        """GitHub API 调用（静默）—— requests 库，代理自适应"""
        import requests as req

        resp = req.get(url, headers=self.headers, timeout=15, proxies={"http": None, "https": None})
        return resp.json()

    def consume_repo(self, repo: dict) -> list:
        """消化一个仓库：克隆→扫描→提取精华→尝试融合"""
        ssh_url = repo.get("ssh_url") or repo["clone_url"]
        repo_name = repo["full_name"]
        results = []

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", ssh_url, tmpdir],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception as e:
                print(f"   ⚠️ 克隆失败: {e}")
                return []

            for py_file in Path(tmpdir).rglob("*.py"):
                if py_file.stat().st_size > 500_000:  # 跳过巨型文件
                    continue

                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # 寻找高价值代码块（按函数/类切分）
                chunks = self._slice_code(content)
                for chunk in chunks:
                    if score_nutrient(chunk) < 20:  # 至少命中2个签名
                        continue
                    if is_poison(chunk):
                        self._quarantine(chunk, repo_name, py_file.name)
                        print(f"   ☠️ 毒物已隔离: {py_file.name}")
                        continue

                    nutrient_name = extract_nutrient_name(chunk)
                    result = self._integrate(chunk, repo_name, nutrient_name)
                    if result:
                        results.append(result)

            # 标记已消费
            self.state["consumed"].append(repo)
            self.save_state()

        return results

    def _slice_code(self, content: str) -> list:
        """把文件切成独立的函数/类块"""
        chunks = []
        lines = content.split("\n")
        buf = []
        in_block = False
        indent_level = 0

        for line in lines:
            stripped = line.rstrip()
            if not in_block:
                if re.match(r"^(async\s+)?def\s+\w+|^class\s+\w+", stripped):
                    in_block = True
                    indent_level = len(line) - len(line.lstrip())
                    buf = [stripped]
            else:
                if (
                    stripped
                    and len(line) - len(line.lstrip()) <= indent_level
                    and not stripped.startswith(" " * (indent_level + 1))
                ):
                    # 回到同缩进级别 → block 结束
                    chunks.append("\n".join(buf))
                    buf = []
                    in_block = False
                    if re.match(r"^(async\s+)?def\s+\w+|^class\s+\w+", stripped):
                        in_block = True
                        indent_level = len(line) - len(line.lstrip())
                        buf = [stripped]
                else:
                    buf.append(stripped)

        if buf:
            chunks.append("\n".join(buf))

        # 去重：如果整块代码完全一样，只保留一份
        seen = set()
        unique = []
        for c in chunks:
            h = hashlib.md5(c.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(c)
        return unique

    def _quarantine(self, code: str, source: str, filename: str):
        """毒物隔离：不吞，存到 quarantine 目录供人工审查"""
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        q_name = f"poison_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(code.encode()).hexdigest()[:8]}.py"
        q_path = QUARANTINE_DIR / q_name
        q_path.write_text(
            f"# QUARANTINED: {source}/{filename}\n# Date: {ts()}\n# Reason: matched POISON_SIGNATURES\n\n{code}",
            encoding="utf-8",
        )
        self.state.setdefault("quarantined", []).append(
            {"source": source, "file": filename, "quarantine": str(q_path), "ts": ts()}
        )

    def _integrate(self, code: str, source: str, nutrient_name: str) -> dict | None:
        """融合养分到 external_nutrients.py，打上 experimental 标签"""
        NUTRIENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 避免重复吸收
        code_hash = hashlib.md5(code.encode()).hexdigest()[:12]
        existing_hashes = {n.get("hash") for n in self.state.get("nutrients", {}).values()}
        if code_hash in existing_hashes:
            print(f"   ⏭️ 已存在，跳过: {nutrient_name}")
            return None

        # 写入
        block = (
            f"\n\n# ═══════════════════════════════════════════════════════════════\n"
            f"# 🦞 Predator Nutrient: {nutrient_name}\n"
            f"# Source: {source}\n"
            f"# Harvested: {ts()}\n"
            f"# Status: EXPERIMENTAL — not production-safe until reviewed\n"
            f"# Hash: {code_hash}\n"
            f"# ═══════════════════════════════════════════════════════════════\n"
            f"{code}\n"
        )

        with open(NUTRIENTS_FILE, "a", encoding="utf-8") as f:
            f.write(block)

        nutrient_id = f"{nutrient_name}_{code_hash}"
        self.state.setdefault("nutrients", {})[nutrient_id] = {
            "name": nutrient_name,
            "source": source,
            "hash": code_hash,
            "harvested": ts(),
            "file": str(NUTRIENTS_FILE),
        }
        self.save_state()

        print(f"   ✅ 吸收营养: {nutrient_name} (score={score_nutrient(code)})")
        return {"nutrient": nutrient_name, "source": source, "hash": code_hash}

    def list_nutrients(self):
        """列出所有已吸收的营养"""
        nutrients = self.state.get("nutrients", {})
        if not nutrients:
            print("[Predator] 尚未吸收任何外来营养。")
            return []

        print(f"\n[Predator] 当前体内营养 ({len(nutrients)} 项):")
        for nid, info in sorted(nutrients.items(), key=lambda x: x[1]["harvested"], reverse=True):
            print(f"  · {info['name']} ← {info['source']} ({info['harvested'][:10]})")
        return list(nutrients.keys())

    def purge_nutrient(self, nutrient_id: str):
        """代谢排泄：删除某个外来营养"""
        nutrients = self.state.get("nutrients", {})
        if nutrient_id not in nutrients:
            print(f"[Predator] 未找到营养: {nutrient_id}")
            return

        info = nutrients.pop(nutrient_id)
        self.state["nutrients"] = nutrients
        self.save_state()
        print(f"[Predator] 已排泄: {info['name']} ← {info['source']}")

    def run(self, daily: bool = True):
        """执行一次狩猎循环"""
        print(f"[Predator] === {ts()} ===")
        results = self.hunt_fresh_meat()
        print(f"[Predator] 本轮吸收 {len(results)} 项外部营养")
        return results


# ═══════════════════════════════════════════════
# CLI: 支持手动运行和进化引擎调度
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="猫抓 GitHub Predator — 开源吞噬者")
    parser.add_argument("--hunt", action="store_true", help="立即狩猎")
    parser.add_argument("--list", action="store_true", help="列出已吸收营养")
    parser.add_argument("--purge", type=str, help="排泄指定营养ID")
    parser.add_argument("--force", action="store_true", help="强制重新狩猎（忽略 last_hunt）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--dry-run", action="store_true", help="干跑不写入")
    args = parser.parse_args()

    p = GitHubPredator()

    if args.force and args.hunt:
        p.state["last_hunt"] = ""
        p.save_state()

    if args.list:
        nutrients = p.list_nutrients()
        if args.json:
            print(json.dumps(nutrients, ensure_ascii=False))

    elif args.purge:
        p.purge_nutrient(args.purge)

    elif args.hunt:
        if args.dry_run:
            print("[Predator] DRY RUN — 只嗅探不吞咽")
            # 模拟狩猎输出
            print("[Predator] 出发狩猎新鲜代码...")
            print("[Predator] DRY RUN 完成（未实际吸收）")
        else:
            results = p.run()
            if args.json:
                print(
                    json.dumps(
                        {"status": "ok", "absorbed": len(results), "nutrients": results},
                        ensure_ascii=False,
                        default=str,
                    )
                )
    else:
        print("用法: python github_predator.py --hunt [--force] [--dry-run] [--json]")
        print("      python github_predator.py --list [--json]")
        print("      python github_predator.py --purge <nutrient_id>")
