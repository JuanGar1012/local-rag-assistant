from __future__ import annotations

import json
from typing import Any

import httpx


def _print_block(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2))
    else:
        print(str(payload))


def main() -> None:
    base_url = "http://127.0.0.1:8000"
    with httpx.Client(timeout=60.0) as client:
        health = client.get(f"{base_url}/health")
        _print_block("GET /health", {"status_code": health.status_code, "body": health.json() if health.headers.get("content-type", "").startswith("application/json") else health.text})

        q1 = client.post(
            f"{base_url}/query",
            json={"question": "What stack does this project use?", "top_k": 5},
        )
        _print_block("POST /query #1", {"status_code": q1.status_code, "body": q1.json() if q1.headers.get("content-type", "").startswith("application/json") else q1.text})

        q2 = client.post(
            f"{base_url}/query",
            json={"question": "What metrics are tracked?", "top_k": 5},
        )
        _print_block("POST /query #2", {"status_code": q2.status_code, "body": q2.json() if q2.headers.get("content-type", "").startswith("application/json") else q2.text})

        summary = client.get(f"{base_url}/metrics/summary")
        _print_block("GET /metrics/summary", {"status_code": summary.status_code, "body": summary.json() if summary.headers.get("content-type", "").startswith("application/json") else summary.text})


if __name__ == "__main__":
    main()
