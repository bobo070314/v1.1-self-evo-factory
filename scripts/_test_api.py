import io
import json
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
r = requests.post(
    "http://localhost:8765/api/estimate",
    json={"model": "Benz E300L 2020", "mileage": 8.6, "condition": "original", "plate": "ABC-123"},
    timeout=10,
)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
