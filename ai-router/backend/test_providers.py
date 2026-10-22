"""Unit tests for the real Ollama adapter without requiring an installed model."""
from __future__ import annotations

import json
import urllib.error
import unittest
from unittest.mock import MagicMock, patch

from providers import (
    MAX_GENERATION_RESPONSE_BYTES,
    ProviderError,
    generate_local_response,
    probe_ollama,
)


class OllamaGenerationTests(unittest.TestCase):
    def setUp(self):
        self.opener = MagicMock()
        self.response = MagicMock()
        self.response.__enter__.return_value = self.response
        self.response.read.return_value = json.dumps({
            "message": {"role": "assistant", "content": "A real-looking test response"},
            "prompt_eval_count": 7,
            "eval_count": 5,
            "total_duration": 1_234_000_000,
            "done": True,
        }).encode("utf-8")
        self.opener.open.return_value = self.response
        self.patch_opener = patch("providers.urllib.request.build_opener", return_value=self.opener)
        self.build_opener = self.patch_opener.start()
        self.addCleanup(self.patch_opener.stop)

    def test_sends_only_to_loopback_and_parses_real_api_shape(self):
        result = generate_local_response(
            "tiny-model", "Please summarize this", system_prompt="You are a test model", timeout=4
        )
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(request.get_method(), "POST")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "tiny-model")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "Please summarize this")
        self.assertEqual(self.opener.open.call_args.kwargs["timeout"], 4.0)
        self.build_opener.assert_called_once()
        self.assertEqual(result["response"], "A real-looking test response")
        self.assertEqual(result["prompt_tokens"], 7)
        self.assertEqual(result["output_tokens"], 5)
        self.assertEqual(result["duration_ms"], 1234)
        self.assertTrue(result["done"])

    def test_cloud_model_is_blocked_before_any_request(self):
        with self.assertRaisesRegex(ProviderError, "مدل‌های ابری"):
            generate_local_response("glm-5.1:cloud", "hello")
        self.opener.open.assert_not_called()

    def test_probe_marks_cloud_and_local_models_explicitly(self):
        self.response.read.return_value = json.dumps({
            "models": [
                {"name": "glm-5.1:cloud", "size": 0, "details": {}},
                {"name": "qwen3:4b-instruct", "size": 123, "details": {"family": "qwen3"}},
            ]
        }).encode("utf-8")
        result = probe_ollama()
        models = {item["name"]: item for item in result["models"]}
        self.assertTrue(models["glm-5.1:cloud"]["is_cloud"])
        self.assertFalse(models["qwen3:4b-instruct"]["is_cloud"])
        self.opener.open.assert_called_once()

    def test_oversized_prompt_is_rejected_before_any_local_request(self):
        with self.assertRaises(ProviderError):
            generate_local_response("tiny-model", "x" * 20_001)
        self.opener.open.assert_not_called()

    def test_oversized_or_invalid_api_response_is_rejected(self):
        self.response.read.return_value = b"x" * (MAX_GENERATION_RESPONSE_BYTES + 1)
        with self.assertRaises(ProviderError):
            generate_local_response("tiny-model", "hello")

        self.response.read.return_value = b"not json"
        with self.assertRaises(ProviderError):
            generate_local_response("tiny-model", "hello")

    def test_http_error_becomes_a_safe_provider_error(self):
        self.opener.open.side_effect = urllib.error.HTTPError(
            "http://127.0.0.1:11434/api/chat", 404, "not found", hdrs=None, fp=None
        )
        with self.assertRaisesRegex(ProviderError, "HTTP 404"):
            generate_local_response("missing-model", "hello")


if __name__ == "__main__":
    unittest.main()
