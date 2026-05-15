---
name: harness
description: Use when the user asks to create, plan, split, approve, or execute Harness phase work in this repository, including generating phases/index.json, phases/<task>/index.json, phases/<task>/stepN.md, or running scripts/execute.py.
---

# Harness

## Overview

Use the Harness workflow to turn a requested implementation task into small, executable, self-contained phase steps. Keep each step narrow enough for an independent Codex session to execute from files alone.

## Workflow

1. Explore `/docs/` first, especially `PRD.md`, `ARCHITECTURE.md`, `ADR.md`, and any other project documents.
2. Read `AGENT.md` for project rules and CRITICAL constraints.
3. Discuss unclear requirements or technical decisions with the user before writing phase files.
4. Draft a multi-step plan and request user approval before creating `phases/` files.
5. After approval, create or update:
   - `phases/index.json`
   - `phases/<task-name>/index.json`
   - `phases/<task-name>/step<N>.md`
6. To execute an approved phase, run:

```bash
python3 scripts/execute.py <task-name>
python3 scripts/execute.py <task-name> --push
```

## Step Design Rules

1. Keep scope minimal: one layer or module per step. Split steps when several modules must change.
2. Make every step self-contained. Do not rely on prior chat context.
3. List required reading, including relevant docs and files created or changed by earlier steps.
4. Specify interfaces, file paths, signatures, and behavioral constraints. Leave implementation details to the executing Codex session unless a rule is critical.
5. Use executable acceptance criteria, such as `npm run build` and `npm test`.
6. Write concrete cautions in the form "Do not do X. Reason: Y."
7. Use kebab-case step names such as `project-setup`, `api-layer`, and `auth-flow`.

## File Formats

Top-level phase index:

```json
{
  "phases": [
    {
      "dir": "0-mvp",
      "status": "pending"
    }
  ]
}
```

Phase detail:

```json
{
  "project": "<project-name>",
  "phase": "<task-name>",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending" },
    { "step": 1, "name": "core-types", "status": "pending" }
  ]
}
```

Use these status values only: `pending`, `completed`, `error`, `blocked`.

Do not add timestamps when creating files. `scripts/execute.py` records `created_at`, `started_at`, `completed_at`, `failed_at`, and `blocked_at`.

## Step Template

```markdown
# Step {N}: {name}

## 읽어야 할 파일

먼저 아래 파일들을 읽고 프로젝트의 아키텍처와 설계 의도를 파악하라:

- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- {이전 step에서 생성/수정된 파일 경로}

이전 step에서 만들어진 코드를 꼼꼼히 읽고, 설계 의도를 이해한 뒤 작업하라.

## 작업

{구체적인 구현 지시. 파일 경로, 클래스/함수 시그니처, 로직 설명을 포함한다.}

## Acceptance Criteria

```bash
npm run build
npm test
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. ARCHITECTURE.md, ADR, AGENT.md의 CRITICAL 규칙을 확인한다.
3. `phases/{task-name}/index.json`의 해당 step을 업데이트한다.

## 금지사항

- {하지 말아야 할 것과 이유}
- 기존 테스트를 깨뜨리지 마라
```

## Execution Semantics

`scripts/execute.py` automatically:

- creates or checks out `feat-<task-name>`
- injects `AGENT.md` and `docs/*.md` into each step prompt
- passes completed step summaries to later steps
- retries failed steps up to three times with prior error feedback
- separates code commits from metadata commits
- records timestamps for phase and step state transitions

If a step is `error`, reset its status to `pending` and remove `error_message` before rerunning. If a step is `blocked`, resolve `blocked_reason`, reset status to `pending`, and remove `blocked_reason`.
