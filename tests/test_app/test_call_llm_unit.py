"""
_call_llm のユニットテスト（Vertex の generate_content をモック）。

渡したプロンプトがそのまま model.generate_content に渡され、
response.text が返り値になることを検証する。
"""
from unittest.mock import MagicMock, patch

import pytest


class TestCallLlmUnit:
    """_call_llm が Vertex を正しく呼び出し、response.text を返す。"""

    def test_call_llm_passes_prompt_and_returns_response_text(self) -> None:
        from app.main import _call_llm

        fake_response = MagicMock()
        fake_response.text = "モック応答テキスト"

        with patch("app.main._get_vertex_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = fake_response
            mock_get_model.return_value = mock_model

            result = _call_llm("テスト用プロンプト")

        mock_get_model.assert_called_once()
        mock_model.generate_content.assert_called_once_with("テスト用プロンプト")
        assert result == "モック応答テキスト"

    def test_call_llm_returns_fallback_when_response_text_empty(self) -> None:
        from app.main import _call_llm

        fake_response = MagicMock()
        fake_response.text = None

        with patch("app.main._get_vertex_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = fake_response
            mock_get_model.return_value = mock_model

            result = _call_llm("プロンプト")

        assert result == "（応答を取得できませんでした）"
