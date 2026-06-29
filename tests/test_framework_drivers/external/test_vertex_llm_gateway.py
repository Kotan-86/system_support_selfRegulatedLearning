# 仕様: docs/spec/application-usecase.md#LlmGateway
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-3-Tutoring
"""VertexLlmGateway の単体テスト（Vertex API はモック）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from application.common.errors import LlmGatewayError
from framework_drivers.external.vertex.vertex_llm_gateway import (
    VertexLlmGateway,
    _format_gateway_error,
)
from tenacity import RetryError


class TestVertexLlmGateway:
    """VertexLlmGateway の基本動作。"""

    def test_generate_returns_model_text(self) -> None:
        gateway = VertexLlmGateway(project_id="test-project", location="us-east4")
        mock_response = MagicMock()
        mock_response.text = "vertex reply"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(gateway, "_get_client", return_value=mock_client):
            result = gateway.generate("hello prompt")

        assert result == "vertex reply"
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-3.5-flash",
            contents="hello prompt",
        )

    def test_generate_raises_when_response_is_empty(self) -> None:
        gateway = VertexLlmGateway(project_id="test-project", location="us-east4")
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(gateway, "_get_client", return_value=mock_client):
            with pytest.raises(LlmGatewayError, match="empty response"):
                gateway.generate("hello prompt")

    def test_get_client_requires_project_and_location(self) -> None:
        gateway = VertexLlmGateway(project_id=None, location=None)

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LlmGatewayError, match="VERTEX_PROJECT_ID"):
                gateway._get_client()

    def test_generate_wraps_unexpected_errors(self) -> None:
        gateway = VertexLlmGateway(project_id="test-project", location="us-east4")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("network down")

        with patch.object(gateway, "_get_client", return_value=mock_client):
            with pytest.raises(LlmGatewayError, match="network down"):
                gateway.generate("hello prompt")

    def test_generate_unwraps_retry_error_to_root_cause(self) -> None:
        gateway = VertexLlmGateway(project_id="test-project", location="us")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError(
            "404 NOT_FOUND Publisher Model `gemini-3.5-flash` was not found"
        )

        with patch.object(gateway, "_get_client", return_value=mock_client):
            with pytest.raises(LlmGatewayError, match="404 NOT_FOUND"):
                gateway.generate("hello prompt")

    def test_format_gateway_error_unwraps_retry_error(self) -> None:
        root = RuntimeError("429 RESOURCE_EXHAUSTED")
        retry_error = RetryError(MagicMock())
        retry_error.last_attempt = MagicMock()
        retry_error.last_attempt.failed = True
        retry_error.last_attempt.exception.return_value = root

        assert _format_gateway_error(retry_error) == (
            "LLM gateway failed: 429 RESOURCE_EXHAUSTED"
        )
