"""Todoist API 클라이언트 (GitHub Composite Action 전용).

진입점: ACTION_MODE 환경 변수에 따라 dispatch.

필수 환경 변수:
    TODOIST_TOKEN
    ACTION_MODE: "create-task" | "close-by-issue"
    PROJECT_NAME
    create-task: ISSUE_NUMBER, ISSUE_TITLE, ISSUE_URL, ISSUE_BODY, LABELS
    close-by-issue: ISSUE_NUMBER, ISSUE_URL
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.todoist.com/api/v1"
DESCRIPTION_MAX_BYTES = 300
DEFAULT_LABELS = "Github issue"


def _request(method, path, data=None):
    """공통 HTTP 호출. 실패 시 stderr 출력 후 sys.exit(1)."""
    token = os.environ["TODOIST_TOKEN"]
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(
        API_BASE + path,
        data=payload,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw, strict=False) if raw else None
            return body, resp.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(
            "❌ Todoist API 실패 (HTTP " + str(e.code) + ") "
            + method + " " + path + ": " + err_body,
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("❌ Todoist 응답 JSON 파싱 실패: " + str(e), file=sys.stderr)
        sys.exit(1)


def _truncate_bytes(text, max_bytes):
    """UTF-8 바이트 기준으로 자르되 멀티바이트 경계 안전 처리."""
    encoded = text.encode("utf-8")[:max_bytes]
    return encoded.decode("utf-8", errors="ignore")


def _parse_labels():
    """LABELS 환경변수를 콤마 구분으로 파싱하고 공백·빈 토큰 제거."""
    raw = os.environ.get("LABELS", DEFAULT_LABELS) or DEFAULT_LABELS
    return [label.strip() for label in raw.split(",") if label.strip()]


def _resolve_project_id(project_name):
    """프로젝트명으로 Todoist 프로젝트 ID 조회."""
    cursor = None
    while True:
        path = "/projects"
        if cursor:
            path += "?cursor=" + urllib.parse.quote(cursor, safe="")

        data, _ = _request("GET", path)
        if isinstance(data, dict):
            projects = data.get("results", [])
            next_cursor = data.get("next_cursor")
        else:
            projects = data or []
            next_cursor = None

        for p in projects:
            if p.get("name") == project_name:
                return p["id"]

        if not next_cursor:
            break
        cursor = next_cursor

    print(
        "❌ Todoist 프로젝트를 찾을 수 없습니다: " + project_name,
        file=sys.stderr,
    )
    sys.exit(1)


def create_task():
    issue_number = os.environ["ISSUE_NUMBER"]
    issue_title = os.environ["ISSUE_TITLE"]
    issue_url = os.environ["ISSUE_URL"]
    issue_body = os.environ.get("ISSUE_BODY", "") or ""

    project_id = _resolve_project_id(os.environ["PROJECT_NAME"])
    labels = _parse_labels()

    truncated = _truncate_bytes(issue_body, DESCRIPTION_MAX_BYTES)
    description = truncated + "\n\n🔗 " + issue_url

    body, _ = _request(
        "POST",
        "/tasks",
        {
            "content": "[#" + issue_number + "] " + issue_title,
            "description": description,
            "project_id": project_id,
            "labels": labels,
        },
    )
    task_id = (body or {}).get("id", "unknown")
    print("✅ Todoist 업무 생성 완료 (task_id: " + str(task_id) + ")")


def close_by_issue():
    issue_number = os.environ["ISSUE_NUMBER"]
    issue_url = os.environ["ISSUE_URL"]

    project_id = _resolve_project_id(os.environ["PROJECT_NAME"])

    prefix = "[#" + issue_number + "]"
    match_id = None
    cursor = None

    while True:
        path = "/tasks?project_id=" + urllib.parse.quote(str(project_id), safe="")
        if cursor:
            path += "&cursor=" + urllib.parse.quote(cursor, safe="")

        data, _ = _request("GET", path)
        if isinstance(data, dict):
            tasks = data.get("results", [])
            next_cursor = data.get("next_cursor")
        else:
            tasks = data or []
            next_cursor = None

        for t in tasks:
            content = t.get("content", "")
            description = t.get("description", "")
            if content.startswith(prefix) and issue_url in description:
                match_id = t["id"]
                break

        if match_id or not next_cursor:
            break
        cursor = next_cursor

    if not match_id:
        print("⚠️  매칭되는 Todoist 업무가 없습니다 (issue #" + issue_number + ")")
        sys.exit(0)

    _request("POST", "/tasks/" + match_id + "/close")
    print("✅ Todoist 업무 완료 처리 (task_id: " + match_id + ")")


def main():
    mode = os.environ.get("ACTION_MODE", "").strip()
    if mode == "create-task":
        create_task()
    elif mode == "close-by-issue":
        close_by_issue()
    else:
        print(
            "❌ ACTION_MODE가 올바르지 않습니다: "
            + repr(mode)
            + " (허용: create-task, close-by-issue)",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
