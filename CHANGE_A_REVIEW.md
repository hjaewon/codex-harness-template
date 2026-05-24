# 변경 A 적용 보고서 — summary/contract 분리

## 1. 개요

다른 세션이 제안한 컨텍스트 정책 개선안 중 **변경 A** 만 선택적으로 적용했다.

- 적용: 이전 step 산출물을 `summary`(사람용 상세) + `contract`(다음 step LLM용 압축 계약) 두 필드로 분리.
- **미적용**: 변경 B(retry 시 lightweight guardrails)는 모델이 docs 읽기를 누락할 리스크가 있어 보류.
- **미적용**: 변경 C 외 다른 제안(focused mode, MAX_RETRIES 축소, status correction mini-prompt, full/focused 스위치)도 전부 보류.

`MAX_RETRIES = 3`, 첫 시도의 full guardrails(`AGENTS.md` + `docs/*.md` 전체) 주입, step.md 전체 전달, AC/테스트/status/commit 강제 규칙은 **그대로 유지**.

---

## 2. 변경 사유

현재 `_build_step_context`는 completed step의 `summary`를 전부 prompt에 누적 주입한다.
- prompt 규칙은 "한 줄 요약"이지만 실제로는 길어지는 경향이 있다.
- 후반 step일수록 누적량이 커진다.

`summary`를 사람용으로 남기되, prompt에는 다음 step이 실제로 알아야 할 공개 계약(API 시그니처, invariant, 산출물 경로)만 1~3줄로 압축해 넣는다.

품질 측면에서 이 변경의 잠재 리스크는 "모델이 contract를 부실하게 써서 정보가 누락되는 경우"다. 이를 줄이기 위해:
- contract가 **없으면** 기존 summary로 fallback (하위 호환).
- 프롬프트에서 contract 작성 가이드(공개 API, invariant, 산출물 경로)를 명시.
- summary는 그대로 보존되므로 사람 검토·재구성 가능.

---

## 3. 변경 내용

### 3.1 `scripts/execute.py` — `_build_step_context` (line 188 부근)

**Before**
```python
@staticmethod
def _build_step_context(index: dict) -> str:
    lines = [
        f"- Step {s['step']} ({s['name']}): {s['summary']}"
        for s in index["steps"]
        if s["status"] == "completed" and s.get("summary")
    ]
    if not lines:
        return ""
    return "## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n"
```

**After**
```python
@staticmethod
def _build_step_context(index: dict) -> str:
    lines = []
    for s in index["steps"]:
        if s["status"] != "completed":
            continue
        # contract 우선, 없으면 summary fallback (하위 호환).
        text = s.get("contract") or s.get("summary")
        if text:
            lines.append(f"- Step {s['step']} ({s['name']}): {text}")
    if not lines:
        return ""
    return "## 이전 Step 산출물 (공개 계약)\n\n" + "\n".join(lines) + "\n\n"
```

차이점:
- `s.get("contract") or s.get("summary")` — contract 있으면 사용, 없으면 summary로 fallback.
- 헤더에 "(공개 계약)" 추가 — 모델에게 "이 섹션은 압축 계약이며, 상세가 필요하면 코드/index.json을 직접 읽어야 한다"는 신호.

### 3.2 `scripts/execute.py` — `_build_preamble`의 작업 규칙 5번

**Before**
```python
f"5. /phases/{self._phase_dir_name}/index.json의 해당 step status를 업데이트하라:\n"
f"   - AC 통과 → \"completed\" + \"summary\" 필드에 이 step의 산출물을 한 줄로 요약\n"
f"   - {self.MAX_RETRIES}회 수정 시도 후에도 실패 → \"error\" + \"error_message\" 기록\n"
f"   - 사용자 개입이 필요한 경우 (API 키, 인증, 수동 설정 등) → \"blocked\" + \"blocked_reason\" 기록 후 즉시 중단\n"
```

**After**
```python
f"5. /phases/{self._phase_dir_name}/index.json의 해당 step status를 업데이트하라:\n"
f"   - AC 통과 → \"completed\" + 아래 두 필드를 모두 기록\n"
f"     · \"summary\": 사람이 보는 상세 기록 (제한 없음, 무엇을/왜/어떻게/특이사항)\n"
f"     · \"contract\": 다음 step LLM이 알아야 할 공개 계약만 1~3줄\n"
f"       (공개 API 시그니처, 핵심 invariant, 새 산출물 경로 등. 예: \"engine.execute_rules(rules_dir, model)->dict 추가. eval/exec 금지 유지.\")\n"
f"   - {self.MAX_RETRIES}회 수정 시도 후에도 실패 → \"error\" + \"error_message\" 기록\n"
f"   - 사용자 개입이 필요한 경우 (API 키, 인증, 수동 설정 등) → \"blocked\" + \"blocked_reason\" 기록 후 즉시 중단\n"
```

차이점:
- `summary` 단일 필드 → `summary` + `contract` 두 필드.
- `summary`는 제한 없음(상세 기록), `contract`는 공개 API/invariant/산출물 경로 중심 1~3줄.
- 예시 한 줄 추가로 모델이 contract 형식을 학습하기 쉽게 만듦.

### 3.3 `scripts/test_execute.py` — 테스트 7개 추가

`TestBuildStepContext`에 6개:
- `test_header_mentions_contract` — 헤더에 "공개 계약" 포함 확인.
- `test_contract_preferred_over_summary` — contract와 summary가 둘 다 있을 때 contract가 prompt에 들어가는지.
- `test_summary_used_when_no_contract` — contract가 없으면 summary로 fallback (기존 동작 유지).
- `test_contract_only_no_summary` — summary 없이 contract만 있어도 정상 동작.
- `test_excludes_when_both_missing` — 둘 다 없으면 해당 step은 prompt에서 제외.

`TestBuildPreamble`에 1개:
- `test_instructs_summary_and_contract_fields` — 프롬프트가 두 필드 모두 지시하는지.

---

## 4. 하위 호환성

- 기존 `summary`만 쓰는 phase는 **그대로 동작**한다. `contract` 미존재 → `summary` fallback.
- 새 phase부터 모델이 `contract`를 채우기 시작하면, 그때부터 prompt에 압축 계약이 주입된다.
- `index.json` 스키마는 새 필드 `contract`를 **추가**할 뿐 기존 필드는 건드리지 않음. 기존 도구·스크립트와 충돌 없음.

---

## 5. 테스트 결과

```
============================= 57 passed in 1.32s ==============================
```

- 기존 50개 테스트 회귀 없음.
- 신규 7개 테스트 모두 통과.

---

## 6. 잔존 리스크와 그에 대한 판단

### 리스크 1: 모델이 contract를 부실하게 작성
- 모델이 1~3줄 contract를 쓰면서 다음 step에 필요한 정보를 빠뜨릴 수 있다.
- 현재 장황한 summary는 정보 누락 측면에서는 안전망이지만, contract로 압축하는 순간 그 안전망이 사라진다.

**완화 장치**
- summary는 그대로 보존되므로 index.json/코드를 보면 복구 가능.
- 헤더가 "공개 계약"임을 명시 → 모델이 "이건 압축본"이라고 인식하고 필요 시 코드를 직접 읽도록 유도.
- 프롬프트에 contract 작성 예시(공개 API, invariant, 산출물 경로)를 명시.

### 리스크 2: contract와 summary 정보 불일치
- 모델이 contract와 summary를 별도로 쓰다 보면 두 필드가 어긋날 수 있다.
- 다만 prompt에는 contract만 들어가므로 다음 step 동작에는 영향 없음. 사람 검토 시에만 confusion 가능.

**완화 장치**
- 본 변경에서는 별도 처리하지 않음. 운영 중 문제가 되면 contract 검증 로직 추가 검토.

### 리스크 3: 기존 phase에서 contract가 없는 동안의 효과
- 이미 진행 중인 phase는 contract 필드가 없어서 `summary` fallback이 동작 → 기존과 100% 동일.
- 즉 본 변경의 토큰 절감 효과는 **새 phase부터** 점진적으로 나타난다.

---

## 7. 의도적으로 적용하지 않은 것

| 제안 | 보류 이유 |
|---|---|
| 변경 B: retry 시 CLAUDE.md만 주입 | codex/claude exec는 stateless라 retry 컨텍스트에 첫 시도 docs 없음. 모델이 docs를 Read tool로 읽지 않으면 정보 누락. 제안자 본인도 "리스크: 모델이 docs 읽기를 누락할 가능성"이라 인정. |
| step type별 docs 선택 주입 (focused mode) | step 분류 오판 시 필요한 컨텍스트 누락. 분류 매핑 자체가 새 유지보수 부담. |
| MAX_RETRIES 축소 (3 → 1~2) | 자가교정 기회 감소. 현재 3회는 status 누락·일시 실패 복구에 충분. |
| 실패 유형별 retry 분기 | 분기 분류 오판 시 회복 가능한 실패를 error로 종결시킬 위험. |
| status correction lightweight prompt | 가벼운 prompt가 CRITICAL 규칙을 누락할 위험. |
| full/focused mode 스위치 | 어느 모드를 쓸지 매번 판단 필요 → 운영 복잡도 증가. |

---

## 8. 변경된 파일 목록

- `scripts/execute.py` — `_build_step_context`, `_build_preamble` 작업 규칙 5번
- `scripts/test_execute.py` — 신규 테스트 7개

`AGENTS.md`, `docs/*.md`, `phases/` 구조, git/checkout/commit 로직, retry 정책은 **변경 없음**.

---

## 9. 다음 단계 (검토자 액션)

1. 위 diff(3.1, 3.2)가 의도와 일치하는지 확인.
2. 새 phase를 만들었을 때 모델이 `contract` 필드를 잘 쓰는지 첫 실사용 단계에서 관찰.
3. 1~2 phase 운영 후 토큰 절감 효과와 contract 품질을 평가.
4. 문제가 발견되면 본 변경만 롤백 가능 (변경 범위가 두 메서드와 7개 테스트로 국한됨).

---

## 10. 검토용 질문

- contract 1~3줄 가이드가 너무 엄격/느슨하지 않은가?
- 헤더 "(공개 계약)" 표현이 모델에게 의도대로 전달될 것인가?
- `contract` 필드명을 다른 이름으로 바꿔야 하는가? (예: `next_step_contract`, `public_contract`)
- 기존 phase의 summary를 retroactive하게 contract로 재작성할 필요가 있는가? (현재 답: 불필요 — fallback이 동작)
