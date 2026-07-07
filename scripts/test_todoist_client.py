"""todoist_client 단위 테스트 (스펙 §7 T1~T6).

네트워크 호출(`_request`)을 모킹하여 로직만 검증한다. 실행:
    python3 -m unittest scripts.test_todoist_client   (저장소 루트)
    python3 -m unittest test_todoist_client            (scripts/ 내부)
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import todoist_client as tc  # noqa: E402

PROJECT = "test-project"
ISSUE_NUMBER = "999"
ISSUE_URL = "https://github.com/o/r/issues/999"


def _base_env(**overrides):
    env = {
        "PROJECT_NAME": PROJECT,
        "ISSUE_NUMBER": ISSUE_NUMBER,
        "ISSUE_URL": ISSUE_URL,
        "TODOIST_TOKEN": "dummy",
    }
    env.update(overrides)
    return env


def _make_fake_request(task, calls):
    """(method, path, data) 를 calls 에 기록하는 가짜 _request.

    task: 매칭 태스크 dict 또는 None(매칭 없음).
    """
    tasks = [task] if task is not None else []

    def fake(method, path, data=None):
        calls.append((method, path, data))
        if method == "GET" and path.startswith("/projects"):
            return {"results": [{"name": PROJECT, "id": "P1"}], "next_cursor": None}, 200
        if method == "GET" and path.startswith("/tasks?project_id="):
            return {"results": tasks, "next_cursor": None}, 200
        if method == "POST" and path.endswith("/close"):
            return None, 204
        if method == "POST" and path.startswith("/tasks/"):
            return {}, 200
        raise AssertionError("예상치 못한 요청: " + method + " " + path)

    return fake


def _task(task_id, labels):
    return {
        "id": task_id,
        "content": "[#" + ISSUE_NUMBER + "] 제목",
        "description": "설명\n\n🔗 " + ISSUE_URL,
        "labels": labels,
    }


class LabelByIssueTest(unittest.TestCase):
    def test_t1_label_added_preserving_existing(self):
        """T1: 기존 라벨 유지 + 배포 대기 추가, 완료 처리 안 함."""
        calls = []
        env = _base_env(LABELS="배포 대기")
        with mock.patch.object(tc, "_request", _make_fake_request(_task("T1", ["기존"]), calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            tc.label_by_issue()
        updates = [c for c in calls if c[0] == "POST" and c[1] == "/tasks/T1"]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0][2], {"labels": ["기존", "배포 대기"]})
        self.assertFalse(any(c[1].endswith("/close") for c in calls))

    def test_t2_idempotent_no_api_call(self):
        """T2: 이미 라벨 존재 → 업데이트 API 미호출."""
        calls = []
        env = _base_env(LABELS="배포 대기")
        with mock.patch.object(tc, "_request", _make_fake_request(_task("T2", ["배포 대기"]), calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            tc.label_by_issue()
        updates = [c for c in calls if c[0] == "POST" and c[1].startswith("/tasks/T2")]
        self.assertEqual(updates, [])

    def test_t3_no_match_exit_zero(self):
        """T3: 매칭 태스크 없음 → exit 0, 업데이트 미호출."""
        calls = []
        env = _base_env(LABELS="배포 대기")
        with mock.patch.object(tc, "_request", _make_fake_request(None, calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                tc.label_by_issue()
        self.assertEqual(cm.exception.code, 0)
        self.assertFalse(any(c[0] == "POST" for c in calls))

    def test_t4_union_preserves_order(self):
        """T4: 기존 2개 + 배포 대기 → 3개 union, 순서 보존."""
        calls = []
        env = _base_env(LABELS="배포 대기")
        with mock.patch.object(tc, "_request", _make_fake_request(_task("T4", ["x", "y"]), calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            tc.label_by_issue()
        updates = [c for c in calls if c[0] == "POST" and c[1] == "/tasks/T4"]
        self.assertEqual(updates[0][2], {"labels": ["x", "y", "배포 대기"]})

    def test_label_by_issue_dispatch_via_main(self):
        """main() 이 label-by-issue 모드를 올바로 dispatch."""
        calls = []
        env = _base_env(ACTION_MODE="label-by-issue", LABELS="배포 대기")
        with mock.patch.object(tc, "_request", _make_fake_request(_task("M1", []), calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            tc.main()
        self.assertTrue(any(c[1] == "/tasks/M1" and c[0] == "POST" for c in calls))


class CloseByIssueRegressionTest(unittest.TestCase):
    def test_t5_close_still_works(self):
        """T5: 리팩토링 후에도 close-by-issue 완료 처리 정상."""
        calls = []
        env = _base_env()
        with mock.patch.object(tc, "_request", _make_fake_request(_task("C1", []), calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            tc.close_by_issue()
        self.assertTrue(any(c == ("POST", "/tasks/C1/close", None) for c in calls))

    def test_close_no_match_exit_zero(self):
        calls = []
        env = _base_env()
        with mock.patch.object(tc, "_request", _make_fake_request(None, calls)), \
                mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                tc.close_by_issue()
        self.assertEqual(cm.exception.code, 0)


class MainDispatchTest(unittest.TestCase):
    def test_t6_invalid_mode_exit_one(self):
        """T6: 잘못된 ACTION_MODE → exit 1."""
        with mock.patch.dict(os.environ, {"ACTION_MODE": "bogus"}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                tc.main()
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
