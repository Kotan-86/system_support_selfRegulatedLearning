# 仕様: docs/spec/application-usecase.md#LlmGateway
# 仕様: docs/spec/framework-drivers-layer.md#Port-対応表
"""Gemini Enterprise Agent Platform（google-genai SDK）による LlmGateway 実装。"""
from __future__ import annotations

import os
from typing import Any

from application.common.errors import LlmGatewayError
from application.tutoring.ports.llm_gateway import LlmGateway
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

_DEFAULT_MODEL_NAME = "gemini-3.5-flash"


def _root_gateway_exception(exc: BaseException) -> BaseException:
    """tenacity RetryError 等を剥がし、根本原因の例外を返す。"""
    if isinstance(exc, RetryError):
        last_attempt = exc.last_attempt
        if last_attempt.failed:
            nested = last_attempt.exception()
            if nested is not None:
                return nested
    cause = exc.__cause__
    if cause is not None:
        return _root_gateway_exception(cause)
    return exc


def _format_gateway_error(exc: BaseException) -> str:
    root = _root_gateway_exception(exc)
    message = str(root).strip() or type(root).__name__
    return f"LLM gateway failed: {message}"


class VertexLlmGateway(LlmGateway):
    """google-genai Client（vertexai=True）でプロンプトから応答を生成する。"""

    def __init__(
        self,
        *,
        project_id: str | None = None,
        location: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._model_name = model_name or os.environ.get(
            "VERTEX_MODEL_NAME", _DEFAULT_MODEL_NAME
        )
        self._client: Any | None = None

    def generate(self, prompt: str) -> str:
        """LLM 応答テキストを返す。失敗時は LlmGatewayError。"""
        if not prompt.strip():
            raise LlmGatewayError("prompt must not be empty")

        try:
            client = self._get_client()

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=10),
            )
            def _generate(prompt_text: str) -> Any:
                return client.models.generate_content(
                    model=self._model_name,
                    contents=prompt_text,
                )

            response = _generate(prompt)
            text = response.text if response and response.text else ""
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(_format_gateway_error(exc)) from exc

        if not text:
            raise LlmGatewayError("LLM gateway returned empty response")

        return text

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        project_id = self._project_id or os.environ.get("VERTEX_PROJECT_ID")
        location = self._location or os.environ.get("VERTEX_LOCATION")
        if not project_id:
            raise LlmGatewayError("VERTEX_PROJECT_ID is not configured")
        if not location:
            raise LlmGatewayError("VERTEX_LOCATION is not configured")

        try:
            from google import genai
        except ImportError as exc:
            raise LlmGatewayError(
                "google-genai is required for VertexLlmGateway"
            ) from exc

        self._client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
        return self._client
