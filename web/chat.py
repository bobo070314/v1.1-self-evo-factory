"""铁龙虾收车 · FastAPI 后端
POST /api/estimate → DeepSeek 估价 (fallback: 随机模拟)
POST /api/lead     → 落盘 leads.json
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
except ImportError:
    print("Missing deps. Run: pip install fastapi uvicorn")
    sys.exit(1)

UTC = timezone.utc
BASE = Path("D:/bobo/openclaw-foreign/workspace")
LEADS_FILE = BASE / ".deploy" / "leads.json"
INDEX_HTML = BASE / "web" / "index.html"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

app = FastAPI(title="铁龙虾收车API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def ensure_leads():
    if not LEADS_FILE.exists():
        LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEADS_FILE.write_text("[]", encoding="utf-8")


@app.get("/")
async def root():
    if INDEX_HTML.exists():
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>铁龙虾收车</h1><p>index.html not found</p>")


@app.post("/api/estimate")
async def estimate(req: Request):
    body = await req.json()
    model = body.get("model", "")
    mileage = float(body.get("mileage", 8))
    condition = body.get("condition", "原版原漆")
    plate = body.get("plate", "")

    if DEEPSEEK_KEY:
        try:
            import requests

            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": '你是二手车估价专家。根据车型、里程、车况给出市场价格区间。返回JSON：{"price":整数,"price_low":整数,"price_high":整数,"confidence":0-1,"analysis":"分析"}',
                        },
                        {
                            "role": "user",
                            "content": f"车型：{model}，里程：{mileage}万公里，车况：{condition}，车牌：{plate}",
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                },
                timeout=15,
            )
            if resp.status_code == 200:
                ds = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(ds)
                data["fallback"] = False
                return data
        except Exception as e:
            print(f"DeepSeek API error: {e}")

    # Fallback mock
    return mock_estimate(model, mileage, condition, plate)


def mock_estimate(model, mileage, condition, plate):
    import random

    base_prices = {
        "奔驰": 180000,
        "宝马": 160000,
        "奥迪": 150000,
        "大众": 90000,
        "丰田": 100000,
        "本田": 95000,
        "日产": 85000,
        "别克": 80000,
        "福特": 80000,
    }
    base = 140000
    for k, v in base_prices.items():
        if k in model:
            base = v
            break
    mile_decay = min(mileage, 35) * 3000
    cond_map = {"原版原漆": 5000, "少量补漆": 0, "有钣金": -8000, "有事故": -20000}
    cond_adj = cond_map.get(condition, 0)
    price = round(max(20000, base - mile_decay + cond_adj + random.randint(-3000, 3000)) / 1000) * 1000
    low = round((price - 12000 + random.randint(0, 4000)) / 1000) * 1000
    high = round((price + 11000 + random.randint(0, 4000)) / 1000) * 1000
    conf = 0.75 + random.random() * 0.15
    return {
        "price": price,
        "price_low": low,
        "price_high": high,
        "confidence": round(conf, 2),
        "analysis": f"基于「{model}」{mileage}万公里 · {condition} 的市场行情分析：\n• 同款近期成交价集中在 {(low / 10000):.1f}-{(high / 10000):.1f} 万\n• 里程折旧约 {(mile_decay / 10000):.1f} 万\n• 车况调整 {cond_adj / 10000:+.1f} 万\n• 本报价有效期 7 天，最终以验车确认为准",
        "fallback": True,
    }


@app.post("/api/lead")
async def lead(req: Request):
    ensure_leads()
    body = await req.json()
    lead = {
        "ts": body.get("ts", datetime.now(UTC).isoformat()),
        "phone": body.get("phone", ""),
        "wechat": body.get("wechat", ""),
        "carInfo": body.get("carInfo", ""),
        "note": body.get("note", ""),
    }
    leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    leads.append(lead)
    LEADS_FILE.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "total": len(leads)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
