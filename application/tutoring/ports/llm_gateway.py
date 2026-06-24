# 仕様: docs/spec/application-usecase.md#LlmGateway
"""LLM 呼び出し Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LlmGateway(ABC):
    """プロンプト文字列から LLM 応答を生成する。"""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """LLM 応答テキストを返す。"""
