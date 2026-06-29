"""
VertexLlmGateway のユニットテスト（google-genai の generate_content をモック）。

渡したプロンプトがそのまま client.models.generate_content に渡され、
response.text が返り値になることを検証する。
"""
from unittest.mock import MagicMock, patch

import pytest

from application.common.errors import LlmGatewayError


class TestVertexLlmGatewayUnit:
    """VertexLlmGateway が google-genai を正しく呼び出し、response.text を返す。"""

    def test_generate_passes_prompt_and_returns_response_text(self) -> None:
        from framework_drivers.external.vertex.vertex_llm_gateway import VertexLlmGateway

        fake_response = MagicMock()
        fake_response.text = "モック応答テキスト"
        gateway = VertexLlmGateway(project_id="test-project", location="us-east4")

        with patch.object(gateway, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = fake_response
            mock_get_client.return_value = mock_client

            result = gateway.generate("テスト用プロンプト")

        mock_get_client.assert_called_once()
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-3.5-flash",
            contents="テスト用プロンプト",
        )
        assert result == "モック応答テキスト"

    def test_generate_raises_when_response_text_empty(self) -> None:
        from framework_drivers.external.vertex.vertex_llm_gateway import VertexLlmGateway

        fake_response = MagicMock()
        fake_response.text = None
        gateway = VertexLlmGateway(project_id="test-project", location="us-east4")

        with patch.object(gateway, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = fake_response
            mock_get_client.return_value = mock_client

            with pytest.raises(LlmGatewayError):
                gateway.generate("プロンプト")
