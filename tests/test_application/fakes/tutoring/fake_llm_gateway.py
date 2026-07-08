# 仕様: docs/spec/application-usecase.md#LlmGateway
"""LlmGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from application.tutoring.ports.llm_gateway import LlmGateway


class FakeLlmGateway(LlmGateway):
    """固定応答を返す Fake LlmGateway。"""

    def __init__(
        self,
        *,
        response: str = "fake-assistant-response",
        json_response: dict | None = None,
    ) -> None:
        self._response = response
        self._json_response = json_response or {
            "utterance_type": "VAGUE_MEMORY",
            "interpretation_state": {},
            "evidence_references": [],
        }
        self.generate_calls: list[str] = []
        self.generate_json_calls: list[tuple[str, str | None]] = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self._response

    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
        self.generate_json_calls.append((prompt, schema_hint))
        return dict(self._json_response)

    def set_response(self, response: str) -> None:
        """テスト用: 返却する応答テキストを変更する。"""
        self._response = response

    def set_json_response(self, json_response: dict) -> None:
        """テスト用: generate_json の返却 dict を変更する。"""
        self._json_response = json_response
