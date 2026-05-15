#!/usr/bin/env python3
"""Block clearly destructive shell commands before Codex runs them."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


BLOCKED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE), "git reset --hard is destructive."),
    (re.compile(r"\bgit\s+clean\s+-[^\n]*[fdx]", re.IGNORECASE), "git clean can delete untracked files."),
    (re.compile(r"\bgit\s+push\b[^\n]*(--force|--force-with-lease|-f)\b", re.IGNORECASE), "force push requires explicit human approval."),
    (re.compile(r"\brm\s+-[^\n]*r[^\n]*f[^\n]*(/|\.\.?)(\s|$)", re.IGNORECASE), "recursive forced delete of a broad path is blocked."),
    (re.compile(r"\bRemove-Item\b[^\n]*\b-Recurse\b[^\n]*\b-Force\b", re.IGNORECASE), "Remove-Item -Recurse -Force is blocked by repo policy."),
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "destructive database command is blocked."),
    (re.compile(r"(\bcurl\b|\bInvoke-WebRequest\b|\biwr\b)[^\n]*(\||;)[^\n]*(\bsh\b|\bbash\b|\biex\b|Invoke-Expression)", re.IGNORECASE), "piping downloaded code into an interpreter is blocked."),
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


def _command_from_event(event: dict[str, Any]) -> str:
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    return ""


def _deny_pre_tool_use(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _deny_permission_request(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "deny",
                "message": reason,
            },
        }
    }


def main() -> int:
    event = _load_event()
    command = _command_from_event(event)

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.search(command):
            hook_event = event.get("hook_event_name")
            payload = _deny_permission_request(reason) if hook_event == "PermissionRequest" else _deny_pre_tool_use(reason)
            print(json.dumps(payload))
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
