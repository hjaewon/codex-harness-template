---
name: harness-review
description: Use when the user asks to review changes in this Harness repository against AGENTS.md, docs/ARCHITECTURE.md, docs/ADR.md, tests, buildability, or CRITICAL project rules.
---

# Harness Review

## Overview

Review repository changes against the Harness project rules and architecture documents. Lead with concrete findings and include the verification status.

## Review Workflow

1. Read these files first:
   - `/AGENTS.md`
   - `/docs/ARCHITECTURE.md`
   - `/docs/ADR.md`
2. Inspect changed files with `git status`, `git diff`, and focused file reads.
3. Check the changed files against the checklist below.
4. Run the relevant build or test commands when available.
5. Report failures with file and line references when possible.

## Checklist

| 항목 | 검증 기준 |
|------|-----------|
| 아키텍처 준수 | 변경사항이 `ARCHITECTURE.md`의 디렉터리 구조와 책임 분리를 따르는가? |
| 기술 스택 준수 | `ADR.md`의 기술 선택을 벗어나지 않았는가? |
| 테스트 존재 | 새 기능이나 동작 변경에 대한 테스트가 있는가? |
| CRITICAL 규칙 | `AGENTS.md`의 CRITICAL 규칙을 위반하지 않았는가? |
| 빌드 가능 | 빌드 또는 테스트 명령이 에러 없이 통과하는가? |

## Output Format

Use this table after listing any high-severity findings:

| 항목 | 결과 | 비고 |
|------|------|------|
| 아키텍처 준수 | ✅/❌ | {상세} |
| 기술 스택 준수 | ✅/❌ | {상세} |
| 테스트 존재 | ✅/❌ | {상세} |
| CRITICAL 규칙 | ✅/❌ | {상세} |
| 빌드 가능 | ✅/❌ | {상세} |

When there are violations, provide specific fixes. When verification could not be run, state the exact command that was skipped or failed and why.
