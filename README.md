# gh-todoist-action

GitHub Issue 이벤트(opened/closed)를 Todoist 업무로 자동 동기화하는 GitHub Composite Action.

- **opened** 이벤트 → 지정한 Todoist 프로젝트에 `[#N] 제목` 형식의 업무 생성
- **closed** 이벤트 → 동일 프로젝트에서 `[#N]` 접두사 + issue URL 매칭하여 업무 완료 처리

Python 3 표준 라이브러리만 사용하여 외부 의존성이 없으며, `actions/setup-python` 없이 GitHub-hosted runner의 기본 Python 3로 동작합니다.

---

## Usage

### 사전 준비

1. Todoist에 동기화 대상 **프로젝트 생성** (예: `link-drawer`, `got-wa`)
2. Todoist API 토큰 발급: 설정 → 통합 → 개발자 → API token
3. 호출 측 GitHub 리포에 secret 등록:
   ```bash
   gh secret set TODOIST_API_TOKEN --repo <owner>/<repo>
   ```

### 모드 1: 이슈 생성 시 업무 등록

`.github/workflows/issue-to-todoist.yml`:

```yaml
name: Issue → Todoist 업무 등록

on:
  issues:
    types: [opened]

jobs:
  create-todoist-task:
    runs-on: ubuntu-latest
    steps:
      - uses: doitasap/gh-todoist-action@v1.1.0
        with:
          mode: create-task
          project-name: link-drawer
          labels: "링크서랍,Github issue"
        env:
          TODOIST_TOKEN: ${{ secrets.TODOIST_API_TOKEN }}

# 라벨에 콤마가 포함되는 경우 JSON 배열 사용:
#   labels: '["곧, 와","Github issue"]'
```

### 모드 2: 이슈 종료 시 업무 완료

`.github/workflows/issue-closed-to-todoist.yml`:

```yaml
name: Issue 종료 → Todoist 업무 완료 처리

on:
  issues:
    types: [closed]

jobs:
  close-todoist-task:
    runs-on: ubuntu-latest
    steps:
      - uses: doitasap/gh-todoist-action@v1.1.0
        with:
          mode: close-by-issue
          project-name: link-drawer
        env:
          TODOIST_TOKEN: ${{ secrets.TODOIST_API_TOKEN }}
```

---

## Inputs

| Input | 필수 | 기본값 | 설명 |
|-------|------|--------|------|
| `mode` | ✓ | — | `create-task` 또는 `close-by-issue` |
| `project-name` | ✓ | — | Todoist 프로젝트명 (정확히 일치) |
| `labels` | — | `Github issue` | `create-task` 시 부착할 라벨. 콤마 구분(`"링크서랍,Github issue"`) 또는 JSON 배열(`'["곧, 와","Github issue"]'`) 지원. 콤마를 포함한 라벨이면 JSON 사용 |
| `issue-number` | — | `${{ github.event.issue.number }}` | GitHub 이슈 번호 |
| `issue-title` | — | `${{ github.event.issue.title }}` | 이슈 제목 (`create-task`에서만 사용) |
| `issue-url` | — | `${{ github.event.issue.html_url }}` | 이슈 URL |
| `issue-body` | — | `${{ github.event.issue.body }}` | 이슈 본문 (300 bytes로 잘림) |

> 기본값은 `issues` 이벤트 컨텍스트에서 자동으로 채워집니다. 다른 이벤트에서 호출하려면 명시적으로 전달해야 합니다.

## Secrets

| Env | 필수 | 설명 |
|-----|------|------|
| `TODOIST_TOKEN` | ✓ | Todoist API token (호출 측에서 `env:`로 전달) |

> ⚠️ Composite Action은 `secrets.*`를 직접 참조할 수 없으므로 호출 측에서 반드시 `env:` 블록으로 토큰을 주입해야 합니다.

---

## 동작 상세

### create-task

1. `PROJECT_NAME`으로 Todoist 프로젝트 ID 조회 (페이지네이션 지원)
2. 본문을 UTF-8 300 bytes로 안전 잘림 + 이슈 URL 첨부
3. `POST /tasks`로 업무 생성, `content`는 `[#N] 제목`, `labels`는 input 파싱 결과

### close-by-issue

1. 프로젝트 ID 조회
2. 해당 프로젝트의 활성 업무를 순회하며 `[#N]` 접두사 + URL 매칭
3. 매칭 시 `POST /tasks/{id}/close` 호출
4. 매칭 실패 시 경고만 출력하고 종료 코드 0 (실패 아님)

---

## Versioning

| 태그 | 변경점 |
|------|--------|
| v1.0.0 | 초기 릴리스. `create-task` / `close-by-issue` 2가지 모드, 콤마 구분 라벨 |
| v1.1.0 | `labels` input에 JSON 배열 지원 (콤마 포함 라벨 안전) |

호출 측 권장: `uses: doitasap/gh-todoist-action@v1.1.0` (또는 더 새 버전).

---

## License

MIT
