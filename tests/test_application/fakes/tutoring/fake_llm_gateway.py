# 仕様: docs/spec/application-usecase.md#LlmGateway
"""LlmGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from application.tutoring.ports.llm_gateway import LlmGateway


class FakeLlmGateway(LlmGateway):
    """固定応答を返す Fake LlmGateway。"""

    def __init__(self, *, response: str = "fake-assistant-response") -> None:
        self._response = response
        self.generate_calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self._response

    def set_response(self, response: str) -> None:
        """テスト用: 返却する応答テキストを変更する。"""
        self._response = response
