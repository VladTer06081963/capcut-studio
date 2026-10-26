import json
import importlib
import threading
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from capcut.lib.model_approval import ApprovalError, create_approval, claim_approval


class ModelApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_writes_private_one_task_artifact(self):
        artifact = create_approval(
            "kie", "model-x", "Illustration for episode 1",
            root=self.root, now=self.now,
        )
        stored = json.loads((self.root / "pending" / f"{artifact['id']}.json").read_text())
        self.assertEqual(stored["state"], "pending")
        self.assertEqual(stored["model_id"], "model-x")
        self.assertEqual(
            datetime.fromisoformat(stored["expires_at"]) - datetime.fromisoformat(stored["approved_at"]),
            timedelta(minutes=30),
        )
        self.assertFalse({"api_key", "price", "cost", "budget"} & stored.keys())
        self.assertEqual((self.root / "pending").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "pending" / f"{artifact['id']}.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_claim_consumes_once_and_checks_exact_scope(self):
        artifact = create_approval(
            "kie", "model-x", "Scene 2 illustration", root=self.root, now=self.now,
        )
        with self.assertRaisesRegex(ApprovalError, "scope"):
            claim_approval(
                artifact["id"], "kie", "model-x", "Different task",
                root=self.root, now=self.now + timedelta(minutes=1),
            )
        claimed = claim_approval(
            artifact["id"], "kie", "model-x", "Scene 2 illustration",
            root=self.root, now=self.now + timedelta(minutes=1),
        )
        self.assertEqual(claimed["state"], "consumed")
        self.assertTrue((self.root / "consumed" / f"{artifact['id']}.json").exists())
        self.assertTrue((self.root / "claims" / f"{artifact['id']}.json").exists())
        with self.assertRaisesRegex(ApprovalError, "does not exist|already claimed"):
            claim_approval(
                artifact["id"], "kie", "model-x", "Scene 2 illustration",
                root=self.root, now=self.now + timedelta(minutes=2),
            )

    def test_claim_rejects_model_mismatch(self):
        artifact = create_approval("kie", "model-x", "Task", root=self.root, now=self.now)
        with self.assertRaisesRegex(ApprovalError, "Provider/model"):
            claim_approval(
                artifact["id"], "kie", "model-y", "Task",
                root=self.root, now=self.now + timedelta(minutes=1),
            )

    def test_expired_approval_is_archived_not_reused(self):
        artifact = create_approval("kie", "model-x", "Task", root=self.root, now=self.now)
        with self.assertRaisesRegex(ApprovalError, "expired"):
            claim_approval(
                artifact["id"], "kie", "model-x", "Task",
                root=self.root, now=self.now + timedelta(minutes=30),
            )
        expired = json.loads((self.root / "expired" / f"{artifact['id']}.json").read_text())
        self.assertEqual(expired["state"], "expired")
        self.assertFalse((self.root / "pending" / f"{artifact['id']}.json").exists())

    def test_concurrent_claims_only_allow_one_winner(self):
        artifact = create_approval("kie", "model-x", "Task", root=self.root, now=self.now)

        def claim():
            try:
                claim_approval(
                    artifact["id"], "kie", "model-x", "Task",
                    root=self.root, now=self.now + timedelta(minutes=1),
                )
                return True
            except ApprovalError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(results.count(True), 1)


class ModelApprovalUiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.ui = importlib.import_module("scripts.model_approval_ui")
        self.server = ThreadingHTTPServer((self.ui.HOST, 0), self.ui.RequestHandler)
        self.port = self.server.server_address[1]
        self.port_patch = patch.object(self.ui, "PORT", self.port)
        self.port_patch.start()
        self.create_patch = patch.object(
            self.ui,
            "create_approval",
            side_effect=lambda provider, model_id, task_scope: create_approval(
                provider, model_id, task_scope, root=self.root,
            ),
        )
        self.create_patch.start()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://{self.ui.HOST}:{self.port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.create_patch.stop()
        self.port_patch.stop()
        self.temp_dir.cleanup()

    def test_local_ui_serves_registry_and_requires_same_origin_for_approval(self):
        with urlopen(self.base_url + "/") as response:
            self.assertEqual(response.status, 200)
            document = response.read().decode()
            self.assertIn('href="/styles.css"', document)
            self.assertIn('src="/app.js"', document)
        with urlopen(self.base_url + "/app.js") as response:
            app = response.read().decode()
            self.assertEqual(response.headers.get_content_type(), "text/javascript")
            self.assertIn('querySelector("#provider-choice")', app)
        with urlopen(self.base_url + "/styles.css") as response:
            self.assertEqual(response.headers.get_content_type(), "text/css")
        with urlopen(self.base_url + "/api/models") as response:
            registry = json.load(response)
        self.assertTrue(registry["models"])

        body = json.dumps({
            "provider": "comfyui",
            "model_id": "locally-selected-model",
            "task_scope": "Concept image for episode 1",
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Origin": self.base_url,
        }
        request = Request(self.base_url + "/api/approve", data=body, headers=headers)
        with urlopen(request) as response:
            self.assertEqual(response.status, 201)
            result = json.load(response)
        artifact_path = self.root / "pending" / f"{result['id']}.json"
        self.assertTrue(artifact_path.exists())

        headers["Origin"] = "https://example.invalid"
        request = Request(self.base_url + "/api/approve", data=body, headers=headers)
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
