# -*- coding: utf-8 -*-
"""
core/local_llm.py v5 — 猫抓本地推理层
GTX 1060 3GB / Ollama 11634 / qwen3.5:2b Q8_0
三级回退：local (Ollama) → cloud (DeepSeek) → offline (规则引擎 + BM25)
"""
import os, json, time, socket, sys, re

# ── 代理清零 ──
for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)

import requests

SESSION = requests.Session()
SESSION.trust_env = False

# ── 配置 ──
OLLAMA_BASE = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11634").rstrip("/")
MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen3.5:2b")
CLOUD_KEY = os.getenv("DEEPSEEK_API_KEY", "")
INFERENCE_TIMEOUT = 120
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "kb")

# ── 网络探测 ──
_ollama_cache = (None, 0.0)
_online_cache = (None, 0.0)

def is_online() -> bool:
    global _online_cache
    v, t = _online_cache
    if v is not None and time.time() - t < 60:
        return v
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 53))
        s.close()
        v = True
    except Exception:
        v = False
    _online_cache = (v, time.time())
    return v

def is_ollama_alive() -> bool:
    global _ollama_cache
    v, t = _ollama_cache
    if v is not None and time.time() - t < 30:
        return v
    try:
        r = SESSION.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        v = r.status_code == 200
    except Exception:
        v = False
    _ollama_cache = (v, time.time())
    return v


# ── Ollama 推理 ──
def _ollama_chat(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 2048, "num_predict": 1024, "temperature": 0.2},
    }
    r = SESSION.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=INFERENCE_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    text = (data.get("response") or "").strip()
    if not text:
        thinking = (data.get("thinking") or "").strip()
        if thinking:
            for marker in ["Final:", "输出:", "Output:", "答：", "答复", "回答:"]:
                if marker in thinking:
                    text = thinking.split(marker)[-1].strip()
                    text = text.split("\n")[0].strip().strip('"').strip("'").strip("*").strip()
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "**", "- "]:
                        if text.startswith(prefix):
                            text = text[len(prefix):].strip()
                    break
            if not text:
                for line in reversed(thinking.split("\n")):
                    line = line.strip()
                    if any('\u4e00' <= c <= '\u9fff' for c in line) and len(line) > 10:
                        if not line.startswith("*") and not line.startswith("1.") and "Option" not in line:
                            text = line.strip('"').strip("'").strip("*").strip()
                            break
    return text or "[本地模型返回空]"


# ── Cloud ──
def _cloud_chat(prompt: str) -> str:
    r = SESSION.post(
        "https://api.deepseek.com/v1/chat/completions",
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
        headers={"Authorization": f"Bearer {CLOUD_KEY}"},
        timeout=30,
    )
    return r.json()["choices"][0]["message"]["content"].strip()


# ── 离线引擎 (Level 3: 规则 + BM25) ──
_offline_rules = None
_bm25 = None
_vector_store = None

def _load_offline_components():
    global _offline_rules, _bm25, _vector_store
    if _offline_rules is None:
        try:
            from core.offline_engine import match as offline_match
            _offline_rules = offline_match
        except ImportError:
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
                from core.offline_engine import match as offline_match
                _offline_rules = offline_match
            except ImportError:
                _offline_rules = False
    if _bm25 is None:
        try:
            from core.bm25_fallback import BM25Fallback
            bm = BM25Fallback()
            # 加载知识库文件
            kb_files = []
            kb_dir = KB_DIR
            if os.path.isdir(kb_dir):
                for fname in os.listdir(kb_dir):
                    if fname.endswith(".md") or fname.endswith(".txt"):
                        with open(os.path.join(kb_dir, fname), "r", encoding="utf-8", errors="replace") as f:
                            kb_files.append(f.read()[:2000])
            if kb_files:
                bm.index(kb_files)
            else:
                # 至少索引自身文档作为回退
                bm.index(["猫抓本地AI助手，离线大脑，前端开发全栈编程。"])
            _bm25 = bm
        except ImportError:
            _bm25 = False

_load_offline_components()

def _offline_chat(prompt: str) -> str:
    """离线三级：规则引擎 -> BM25 检索 -> 硬回退"""
    # 1) 规则引擎
    if _offline_rules and _offline_rules is not False:
        resp, rule = _offline_rules(prompt)
        if rule:  # 命中规则
            return f"[离线规则:{rule}] {resp}"

    # 2) BM25 知识库检索
    if _bm25 and _bm25 is not False:
        try:
            results = _bm25.search(prompt, top_k=2)
            if results:
                snippets = [r[2][:200] for r in results if r[1] > 0.3]
                if snippets:
                    return f"[离线检索] {snippets[0]}"
        except Exception:
            pass

    # 3) 硬回退
    p = prompt.lower()
    if any(kw in p for kw in ["你好", "hello", "hi", "在吗", "谁"]):
        return "猫抓离线引擎就绪。无网络、无模型，纯规则+检索模式。"
    if any(kw in p for kw in ["代码", "code", "bug", "error"]):
        return "[离线] 代码分析需要 LLM。请启动 Ollama 或配置 DEEPSEEK_API_KEY。"
    return f"[离线] 猫抓离线模式。提示：启动 Ollama 获得完整能力。"


# ── 统一入口 ──
def chat(prompt: str) -> tuple:
    # Level 1: Ollama 本地
    if is_ollama_alive():
        try:
            return _ollama_chat(prompt), "local"
        except Exception as e:
            print(f"[local_llm] local fail: {e}", file=sys.stderr)

    # Level 2: Cloud
    if CLOUD_KEY and is_online():
        try:
            return _cloud_chat(prompt), "cloud"
        except Exception as e:
            print(f"[local_llm] cloud fail: {e}", file=sys.stderr)

    # Level 3: 离线
    return _offline_chat(prompt), "offline"


def health() -> dict:
    return {
        "ollama_alive": is_ollama_alive(),
        "model": MODEL,
        "internet": is_online(),
        "cloud_key": bool(CLOUD_KEY),
        "offline_engine": _offline_rules is not None and _offline_rules is not False,
        "bm25": _bm25 is not None and _bm25 is not False,
    }


# ── CLI ──
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--health" in sys.argv:
        print(json.dumps(health(), indent=2, ensure_ascii=False))
    else:
        prompt = sys.argv[1] if len(sys.argv) > 1 else "你好"
        text, src = chat(prompt)
        print(f"[{src}] {text}")
