"""Persistence and API safety tests for the local AI Router backend."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server as api
from store import Store, StoreError


def sample_plan():
    return {
        "title": "یک پژوهش علمی درباره خواب",
        "goal": "یک پژوهش علمی درباره خواب با منابع معتبر تهیه کن.",
        "quality": "high",
        "tokenMode": "aggressive",
        "budget": "zero",
        "costPolicy": "zero-cost-only",
        "executionMode": "simulation-only",
        "tasks": [
            {"id": 1, "type": "research", "name": "تحقیق", "kind": "Research"},
            {"id": 2, "type": "writing", "name": "نگارش", "kind": "Writing"},
        ],
        "totalTokens": 320,
        "estimateType": "heuristic",
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp_dir.name) / "test.sqlite3")
        self.store.get_workspace()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_workspace_is_persistent_and_has_stable_id(self):
        first = self.store.get_workspace()["project"]
        second = self.store.get_workspace()["project"]
        self.assertEqual(first["id"], "default")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["created_at"], second["created_at"])

    def test_plan_versions_tasks_and_audit_events_are_saved(self):
        first = self.store.create_plan(sample_plan(), '{"request":"a"}')
        second = self.store.create_plan(sample_plan(), '{"request":"b"}')
        self.assertEqual(first["version"], 1)
        self.assertEqual(second["version"], 2)
        self.assertEqual(len(first["plan"]["tasks"]), 2)
        self.assertEqual([item["version"] for item in self.store.list_plans()], [2, 1])
        event_types = [event["event_type"] for event in self.store.list_events()]
        self.assertEqual(event_types.count("plan_created"), 2)

        reopened = Store(Path(self.temp_dir.name) / "test.sqlite3")
        self.assertEqual(len(reopened.list_plans()), 2)

    def test_approval_rejects_changed_fingerprint(self):
        record = self.store.create_plan(sample_plan(), '{"request":"original"}')
        with self.assertRaises(StoreError) as caught:
            self.store.approve_plan(record["id"], '{"request":"changed"}')
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.store.get_plan(record["id"])["status"], "draft")

    def test_simulation_requires_approval_and_never_marks_tasks_succeeded(self):
        record = self.store.create_plan(sample_plan(), '{"request":"stable"}')
        with self.assertRaises(StoreError):
            self.store.mark_simulated(record["id"])
        approved = self.store.approve_plan(record["id"], '{"request":"stable"}')
        self.assertEqual(approved["status"], "approved")
        finished = self.store.mark_simulated(record["id"])
        self.assertEqual(finished["status"], "simulated")
        self.assertEqual(finished["plan"]["executionMode"], "simulation-only")
        self.assertEqual(self.store.list_events()[0]["event_type"], "simulation_completed")

    def test_double_approval_is_rejected(self):
        record = self.store.create_plan(sample_plan(), '{"request":"stable"}')
        self.store.approve_plan(record["id"], '{"request":"stable"}')
        with self.assertRaises(StoreError) as caught:
            self.store.approve_plan(record["id"], '{"request":"stable"}')
        self.assertEqual(caught.exception.status_code, 409)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_store = api.STORE
        api.STORE = Store(Path(self.temp_dir.name) / "api.sqlite3")
        self.httpd = api.ThreadingHTTPServer(("127.0.0.1", 0), api.RouterHandler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        api.STORE = self.previous_store
        self.temp_dir.cleanup()

    def request_json(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=data, headers=request_headers)
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_marks_ai_disconnected_and_paid_providers_disabled(self):
        status, result = self.request_json("/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(result["ai_connected"])
        self.assertFalse(result["paid_providers_enabled"])

    def test_create_approve_and_simulate_plan_api(self):
        self.request_json("/api/workspace")
        status, created = self.request_json("/api/plans", {
            "project_id": "default",
            "fingerprint": '{"request":"stable"}',
            "plan": sample_plan(),
        })
        self.assertEqual(status, 201)
        plan_id = created["record"]["id"]

        with self.assertRaises(HTTPError) as caught:
            self.request_json(f"/api/plans/{plan_id}/approve", {"fingerprint": "changed"})
        self.assertEqual(caught.exception.code, 409)

        status, approved = self.request_json(
            f"/api/plans/{plan_id}/approve", {"fingerprint": '{"request":"stable"}'}
        )
        self.assertEqual(status, 200)
        self.assertEqual(approved["record"]["status"], "approved")

        status, simulated = self.request_json(f"/api/plans/{plan_id}/simulation", {})
        self.assertEqual(status, 200)
        self.assertEqual(simulated["record"]["status"], "simulated")
        self.assertFalse(simulated["real_execution"])

    def test_foreign_origin_is_rejected(self):
        request = Request(
            self.base + "/api/health",
            headers={"Origin": "https://attacker.example"},
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 403)

    def test_provider_or_nonzero_budget_plan_is_rejected(self):
        bad_plan = sample_plan()
        bad_plan["budget"] = "unknown"
        with self.assertRaises(HTTPError) as caught:
            self.request_json("/api/plans", {
                "project_id": "default",
                "fingerprint": "fingerprint",
                "plan": bad_plan,
            })
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
