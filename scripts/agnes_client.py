import json, os, sys, urllib.request, urllib.error

API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
API_KEY = os.environ.get("AGNES_API_KEY", "")
MODEL = "agnes-2.5-flash"

def call_llm(prompt, model=MODEL, max_tokens=1024):
    """直接调用 agnes OpenAI 兼容端点，返回回复文本或抛异常。"""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

if __name__ == "__main__":
    if not API_KEY:
        print("FAIL: AGNES_API_KEY 未设置"); sys.exit(1)
    try:
        out = call_llm("只回复两个字：通了")
        print("AGENT_LLM_OK:", repr(out))
    except urllib.error.HTTPError as e:
        print("HTTP_ERROR", e.code, e.read().decode("utf-8", "replace")[:400])
        sys.exit(1)
    except Exception as e:
        print("ERR", type(e).__name__, e)
        sys.exit(1)
