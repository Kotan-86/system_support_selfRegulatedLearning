# 仕様: docs/spec/application-usecase.md#LlmGateway
"""LlmGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from application.tutoring.ports.llm_gateway import LlmGateway


_DEFAULT_STUDENT_JSON: dict = {
    "utterance_type": "VAGUE_MEMORY",
    "interpretation_state": {},
    "evidence_references": [],
}

_DEFAULT_PEDAGOGICAL_JSON: dict = {
    "dialogue_move": "JOINT_EVIDENCE_CHECK",
    "response_budget": {
        "max_sentences": 4,
        "max_questions": 1,
        "scaffolding_level": "high",
        "allow_composite_turn": False,
    },
    "interface_instructions": "学習者の発話に応じて証拠を確認する",
    "evidence_to_surface": [],
}


class FakeLlmGateway(LlmGateway):
    """固定応答を返す Fake LlmGateway。"""

    def __init__(
        self,
        *,
        response: str = "fake-assistant-response",
        json_response: dict | None = None,
    ) -> None:
        self._response = response
        self._forced_json_response = json_response
        self._student_json_response = dict(_DEFAULT_STUDENT_JSON)
        self._pedagogical_json_response = dict(_DEFAULT_PEDAGOGICAL_JSON)
        self.generate_calls: list[str] = []
        self.generate_json_calls: list[tuple[str, str | None]] = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self._response

    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
        self.generate_json_calls.append((prompt, schema_hint))
        if self._forced_json_response is not None:
            return dict(self._forced_json_response)
        if "ITS Pedagogical Model (Stage 2)" in prompt:
            return dict(self._pedagogical_json_response)
        if "ITS Student Model (Stage 1)" in prompt:
            return dict(self._student_json_response)
        return dict(self._student_json_response)

    def set_response(self, response: str) -> None:
        """テスト用: 返却する応答テキストを変更する。"""
        self._response = response

    def set_json_response(self, json_response: dict) -> None:
        """テスト用: generate_json の返却 dict を全 Stage で強制する。"""
        self._forced_json_response = json_response
