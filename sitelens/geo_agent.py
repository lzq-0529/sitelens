"""Minimal weekly GEO agent: pull tasks, optionally call an OpenAI-compatible API, ingest."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _json(method: str, url: str, *, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"content-type": "application/json", "x-geo-token": token},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _llm_answer(query: str) -> str:
    endpoint = str(os.environ.get("SITELENS_LLM_URL") or "").strip()
    key = str(os.environ.get("SITELENS_LLM_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    model = str(os.environ.get("SITELENS_LLM_MODEL") or "gpt-4o-mini").strip()
    if not endpoint or not key:
        raise RuntimeError("未配置 SITELENS_LLM_URL + SITELENS_LLM_KEY，无法自动提问。请用 --dry-run 或自己写 Agent。")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你在做品牌可见性抽检。简短回答用户的问题，并尽量给出官网链接。"},
            {"role": "user", "content": query},
        ],
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions" if not endpoint.endswith("/chat/completions") else endpoint,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str((((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or "").strip()


def run(base_url: str, token: str, *, dry_run: bool = True) -> dict[str, Any]:
    base = base_url.rstrip("/")
    tasks = _json("GET", f"{base}/api/geo/tasks", token=token)
    due = tasks.get("due_platforms") or []
    if not due:
        due = [item for item in (tasks.get("all_platforms") or []) if item.get("is_due")]
    prompts = (tasks.get("prompts") or {}).get("cn") or []
    query = prompts[0] if prompts else "这个独立站靠谱吗？官网是哪一个？"
    planned = [{"platform": item.get("id") or item.get("platform"), "query": query} for item in due]
    if dry_run:
        return {"ok": True, "dry_run": True, "due_count": len(planned), "items": planned}
    items = []
    for item in planned:
        items.append({"platform": item["platform"], "query": query, "answer": _llm_answer(query), "sources": []})
    if not items:
        return {"ok": True, "updated_platforms": [], "message": "本周没有到期平台"}
    ingested = _json("POST", f"{base}/api/geo/ingest", token=token, payload={"agent": "custom", "items": items})
    return ingested


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m sitelens.manage geo-agent")
    parser.add_argument("--base-url", default=os.environ.get("SITELENS_BASE_URL") or "http://127.0.0.1:8788")
    parser.add_argument("--token", default=os.environ.get("SITELENS_GEO_TOKEN") or "")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args(argv)
    if not args.token:
        from . import config

        args.token = config.geo_token()
    result = run(args.base_url, args.token, dry_run=args.dry_run or not os.environ.get("SITELENS_LLM_URL"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
