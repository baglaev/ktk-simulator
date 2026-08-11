"""Minimal OpenAI-compatible Chat Completions client.

The implementation uses only the Python standard library and is provider
agnostic. OpenRouter remains the default provider. A locally deployed vLLM
endpoint in VK Cloud can be selected explicitly through environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    """Base error safe to handle without exposing an API key."""


class LLMConfigurationError(LLMError):
    pass


class LLMRequestError(LLMError):
    pass


class LLMResponseError(LLMError):
    pass


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise LLMConfigurationError("AI_LLM_ENABLED must be true or false")


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = False
    provider: str = "openrouter"
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = ""
    fallback_model: str | None = None
    timeout_seconds: float = 45.0
    max_tokens: int = 1200
    temperature: float = 0.2
    data_collection: str = "deny"
    site_url: str | None = None
    app_name: str = "KTK ELOU-AVT AI"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "LLMConfig":
        source = environ if environ is not None else os.environ
        provider = _normalize_provider(source.get("AI_LLM_PROVIDER", "openrouter"))
        if provider == "vk_cloud":
            # Do not inherit the generic/OpenRouter endpoint. An old .env must
            # never route VK Cloud traffic back to an external provider.
            api_key = source.get("AI_VK_CLOUD_API_KEY")
            base_url = source.get(
                "AI_VK_CLOUD_BASE_URL", "http://127.0.0.1:8001/v1"
            )
            model = source.get("AI_VK_CLOUD_MODEL", "")
            fallback_model = ""
        else:
            api_key = source.get("AI_LLM_API_KEY") or source.get(
                "OPENROUTER_API_KEY"
            )
            base_url = source.get(
                "AI_LLM_BASE_URL", "https://openrouter.ai/api/v1"
            )
            model = source.get("AI_LLM_MODEL", "")
            fallback_model = source.get("AI_LLM_FALLBACK_MODEL", "")
        return cls(
            enabled=_as_bool(source.get("AI_LLM_ENABLED"), default=bool(api_key)),
            provider=provider,
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            model=model.strip(),
            fallback_model=fallback_model.strip() or None,
            timeout_seconds=float(source.get("AI_LLM_TIMEOUT_SECONDS", "45")),
            max_tokens=int(source.get("AI_LLM_MAX_TOKENS", "1200")),
            temperature=float(source.get("AI_LLM_TEMPERATURE", "0.2")),
            data_collection=source.get("AI_LLM_DATA_COLLECTION", "deny"),
            site_url=source.get("AI_LLM_SITE_URL") or None,
            app_name=source.get("AI_LLM_APP_NAME", "KTK ELOU-AVT AI"),
        )

    def validate(self) -> None:
        if not self.enabled:
            raise LLMConfigurationError("LLM integration is disabled")
        if self.provider not in {"openrouter", "vk_cloud"}:
            raise LLMConfigurationError(
                "AI_LLM_PROVIDER must be openrouter or vk_cloud"
            )
        if not self.api_key:
            raise LLMConfigurationError(
                "API key for the selected LLM provider is not configured"
            )
        if not self.base_url.startswith(("https://", "http://")):
            raise LLMConfigurationError("AI_LLM_BASE_URL must be an HTTP(S) URL")
        if not self.model:
            raise LLMConfigurationError("AI_LLM_MODEL must not be empty")
        if self.timeout_seconds <= 0:
            raise LLMConfigurationError("AI_LLM_TIMEOUT_SECONDS must be positive")
        if self.max_tokens <= 0:
            raise LLMConfigurationError("AI_LLM_MAX_TOKENS must be positive")
        if not 0 <= self.temperature <= 2:
            raise LLMConfigurationError("AI_LLM_TEMPERATURE must be between 0 and 2")
        if self.data_collection not in {"allow", "deny"}:
            raise LLMConfigurationError(
                "AI_LLM_DATA_COLLECTION must be allow or deny"
            )

    @property
    def is_openrouter(self) -> bool:
        return "openrouter.ai" in self.base_url.lower()


def _normalize_provider(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "openrouter": "openrouter",
        "vk": "vk_cloud",
        "vkcloud": "vk_cloud",
        "vk_cloud": "vk_cloud",
    }
    try:
        return aliases[normalized]
    except KeyError as error:
        raise LLMConfigurationError(
            "AI_LLM_PROVIDER must be openrouter or vk_cloud"
        ) from error


@dataclass(frozen=True)
class CompletionResult:
    content: str
    requested_model: str
    resolved_model: str
    usage: Mapping[str, int]
    fallback_used: bool = False
    fallback_model: str | None = None


UrlOpen = Callable[..., Any]


class OpenAICompatibleClient:
    """Call ``/chat/completions`` using an OpenAI-compatible payload."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        urlopen_impl: UrlOpen = urlopen,
    ) -> None:
        self.config = config or LLMConfig.from_env()
        self._urlopen = urlopen_impl

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> CompletionResult:
        self.config.validate()
        try:
            return self._complete_json_with_model(
                model=self.config.model,
                system_prompt=system_prompt,
                user_payload=user_payload,
            )
        except (LLMRequestError, LLMResponseError) as primary_error:
            fallback_model = self.config.fallback_model
            if (
                not self.config.is_openrouter
                or not fallback_model
                or fallback_model == self.config.model
            ):
                raise
            try:
                fallback = self._complete_json_with_model(
                    model=fallback_model,
                    system_prompt=system_prompt,
                    user_payload=user_payload,
                )
            except (LLMRequestError, LLMResponseError) as fallback_error:
                raise LLMRequestError(
                    "primary and fallback LLM requests failed: "
                    f"primary={primary_error}; fallback={fallback_error}"
                ) from fallback_error
            return CompletionResult(
                content=fallback.content,
                requested_model=self.config.model,
                resolved_model=fallback.resolved_model,
                usage=fallback.usage,
                fallback_used=True,
                fallback_model=fallback_model,
            )

    def _complete_json_with_model(
        self,
        *,
        model: str,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> CompletionResult:
        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.config.is_openrouter:
            request_body["provider"] = {
                "data_collection": self.config.data_collection
            }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.is_openrouter:
            if self.config.site_url:
                headers["HTTP-Referer"] = self.config.site_url
            if self.config.app_name:
                headers["X-OpenRouter-Title"] = self.config.app_name

        request = Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except HTTPError as error:
            raise LLMRequestError(self._http_error_message(error)) from error
        except (URLError, TimeoutError, OSError) as error:
            raise LLMRequestError("LLM provider is unavailable") from error

        try:
            payload = json.loads(raw_response)
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            resolved_model = str(payload.get("model", model))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LLMResponseError("LLM provider returned an invalid response") from error
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("LLM provider returned empty content")

        raw_usage = payload.get("usage", {})
        usage = {
            str(key): int(value)
            for key, value in raw_usage.items()
            if isinstance(value, int)
        } if isinstance(raw_usage, Mapping) else {}
        return CompletionResult(
            content=content,
            requested_model=model,
            resolved_model=resolved_model,
            usage=usage,
        )

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        """Keep provider diagnostics but omit prompts and other metadata."""

        prefix = f"LLM provider returned HTTP {error.code}"
        try:
            raw_body = error.read().decode("utf-8")
            payload = json.loads(raw_body)
            detail = payload.get("error", {})
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return prefix
        if not isinstance(detail, Mapping):
            return prefix
        message = detail.get("message")
        metadata = detail.get("metadata", {})
        error_type = (
            metadata.get("error_type") if isinstance(metadata, Mapping) else None
        )
        parts = [prefix]
        if isinstance(message, str) and message.strip():
            normalized = " ".join(message.split())[:300]
            parts.append(normalized)
        if isinstance(error_type, str) and error_type:
            parts.append(f"error_type={error_type}")
        return ": ".join(parts)


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating a Markdown JSON fence."""

    candidate = content.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise LLMResponseError("LLM content is not valid JSON") from error
    if not isinstance(payload, dict):
        raise LLMResponseError("LLM content must be a JSON object")
    return payload
