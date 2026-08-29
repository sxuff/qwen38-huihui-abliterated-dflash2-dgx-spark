#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(url: str, api_key: str | None, payload: dict | None = None, timeout: int = 10) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--expected-model", required=True)
    p.add_argument("--api-key-file", type=Path)
    p.add_argument("--timeout-seconds", type=int, default=720)
    p.add_argument("--canary-prompt")
    p.add_argument("--canary-expected")
    args = p.parse_args()
    if bool(args.canary_prompt) != bool(args.canary_expected):
        raise SystemExit("canary prompt and expected text must be provided together")
    api_key = args.api_key_file.read_text().strip() if args.api_key_file else None
    deadline = time.monotonic() + args.timeout_seconds
    last_error = None
    models = None
    while time.monotonic() < deadline:
        try:
            models = request(args.base_url.rstrip("/") + "/v1/models", api_key, timeout=5)
            ids = [row.get("id") for row in models.get("data", [])]
            if args.expected_model in ids:
                break
            last_error = f"model identity mismatch: expected={args.expected_model} ids={ids}"
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2)
    else:
        raise SystemExit(f"endpoint readiness failed: {last_error}")

    receipt = {"expected_model": args.expected_model, "models": models, "canary": None}
    if args.canary_prompt:
        payload = {
            "model": args.expected_model,
            "messages": [{"role": "user", "content": args.canary_prompt}],
            "temperature": 0,
            "max_tokens": 32,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        result = request(
            args.base_url.rstrip("/") + "/v1/chat/completions",
            api_key,
            payload=payload,
            timeout=300,
        )
        content = result["choices"][0]["message"].get("content", "").strip()
        if content != args.canary_expected:
            raise SystemExit(
                f"restored generation canary mismatch: expected={args.canary_expected!r} actual={content!r}"
            )
        receipt["canary"] = {
            "content": content,
            "finish_reason": result["choices"][0].get("finish_reason"),
            "usage": result.get("usage"),
        }
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
