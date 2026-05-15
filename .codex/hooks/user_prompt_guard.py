#!/usr/bin/env python3
"""Stop prompts that appear to include high-risk credentials."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI API key-like value"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key-like value"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "GitHub token-like value"),
]


def _load_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    event = _load_event()
    prompt = event.get("prompt", "")
    if not isinstance(prompt, str):
        return 0

    for pattern, label in SECRET_PATTERNS:
        if pattern.search(prompt):
            print(json.dumps({
                "continue": False,
                "stopReason": "Potential secret detected in prompt.",
                "systemMessage": f"Prompt blocked: found {label}. Remove the credential and try again.",
            }))
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
