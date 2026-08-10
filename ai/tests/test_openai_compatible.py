from __future__ import annotations

import json
import unittest
from io import BytesIO
from urllib.error import HTTPError, URLError

from ai.openai_compatible import (
    LLMConfig,
    LLMConfigurationError,
    LLMRequestError,
    OpenAICompatibleClient,
    parse_json_object,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_config_uses_openrouter_defaults(self) -> None:
        config = LLMConfig.from_env({"OPENROUTER_API_KEY": "secret"})
        self.assertTrue(config.enabled)
        self.assertEqual(config.model, "openrouter/free")
        self.assertEqual(config.base_url, "https://openrouter.ai/api/v1")

    def test_missing_key_is_rejected(self) -> None:
        with self.assertRaises(LLMConfigurationError):
            LLMConfig(enabled=True).validate()

    def test_openai_compatible_request_and_response(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse(
                {
                    "model": "openai/gpt-oss-20b:free",
                    "choices": [{"message": {"content": "{\"ok\": true}"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                }
            )

        config = LLMConfig(
            enabled=True,
            api_key="secret",
            site_url="https://example.test",
        )
        result = OpenAICompatibleClient(
            config, urlopen_impl=fake_urlopen
        ).complete_json(system_prompt="system", user_payload={"test": True})

        self.assertEqual(
            captured["url"], "https://openrouter.ai/api/v1/chat/completions"
        )
        self.assertEqual(captured["body"]["model"], "openrouter/free")
        self.assertEqual(
            captured["body"]["response_format"], {"type": "json_object"}
        )
        self.assertEqual(
            captured["body"]["provider"], {"data_collection": "deny"}
        )
        self.assertEqual(result.resolved_model, "openai/gpt-oss-20b:free")
        self.assertEqual(result.usage["prompt_tokens"], 10)
        self.assertNotIn("secret", json.dumps(captured["body"]))

    def test_openrouter_fields_are_not_sent_to_another_provider(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(
                {
                    "model": "local-model",
                    "choices": [{"message": {"content": "{\"ok\": true}"}}],
                }
            )

        client = OpenAICompatibleClient(
            LLMConfig(
                enabled=True,
                api_key="secret",
                base_url="http://127.0.0.1:1234/v1",
                model="local-model",
            ),
            urlopen_impl=fake_urlopen,
        )
        client.complete_json(system_prompt="system", user_payload={})
        self.assertNotIn("provider", captured["body"])

    def test_network_failure_is_wrapped(self) -> None:
        def failing_urlopen(_request, timeout):
            raise URLError(f"unavailable after {timeout}")

        client = OpenAICompatibleClient(
            LLMConfig(enabled=True, api_key="secret"),
            urlopen_impl=failing_urlopen,
        )
        with self.assertRaises(LLMRequestError):
            client.complete_json(system_prompt="system", user_payload={})

    def test_http_error_keeps_safe_provider_reason(self) -> None:
        def failing_urlopen(request, timeout):
            body = json.dumps(
                {
                    "error": {
                        "code": 403,
                        "message": "Request blocked by a guardrail",
                        "metadata": {
                            "error_type": "permission_denied",
                            "flagged_input": "must not be exposed",
                        },
                    }
                }
            ).encode("utf-8")
            raise HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(body))

        client = OpenAICompatibleClient(
            LLMConfig(enabled=True, api_key="secret"),
            urlopen_impl=failing_urlopen,
        )
        with self.assertRaises(LLMRequestError) as raised:
            client.complete_json(system_prompt="system", user_payload={})
        message = str(raised.exception)
        self.assertIn("Request blocked by a guardrail", message)
        self.assertIn("error_type=permission_denied", message)
        self.assertNotIn("must not be exposed", message)

    def test_markdown_fenced_json_is_accepted(self) -> None:
        self.assertEqual(parse_json_object("```json\n{\"ok\": true}\n```"), {"ok": True})


if __name__ == "__main__":
    unittest.main()
