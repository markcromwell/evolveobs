# Unit tests for EVOLVE Observability. Uses the app factory for an isolated instance.
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import create_app
from app.config import Settings

client = TestClient(create_app())


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_settings_fields():
    # Test default values with clean environment
    with patch.dict(os.environ, {}, clear=True):
        clean_settings = Settings()
        assert clean_settings.x_api_key == ""
        assert clean_settings.mcp_url == "http://mcp-internal"
        assert clean_settings.request_timeout == 5.0

    # Test environment overrides
    env_override = {
        "X_API_KEY": "test-key",
        "MCP_URL": "http://mcp-override",
        "REQUEST_TIMEOUT": "10.5"
    }
    with patch.dict(os.environ, env_override, clear=True):
        override_settings = Settings()
        assert override_settings.x_api_key == "test-key"
        assert override_settings.mcp_url == "http://mcp-override"
        assert override_settings.request_timeout == 10.5

    # Test UAT_MCP_URL override fallback
    env_override_uat = {
        "UAT_MCP_URL": "http://mcp-uat-override"
    }
    with patch.dict(os.environ, env_override_uat, clear=True):
        uat_settings = Settings()
        assert uat_settings.mcp_url == "http://mcp-uat-override"


def test_get_index_success():
    mock_samples = [
        {
            "cycle_id": "cycle-123",
            "arm": "treatment",
            "source": "sensor-1",
            "measured_at": "2026-07-07T00:00:00Z",
            "metrics": {"value": 42.0}
        },
        {
            "cycle_id": "cycle-124",
            "arm": "control",
            "source": "sensor-2",
            "measured_at": "2026-07-07T01:00:00Z",
            "metrics": {"value": 84.0}
        }
    ]
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"samples": mock_samples}
        mock_get.return_value = mock_resp

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text

        # Verify exactly two meter-sample-row entries render
        assert html.count('data-testid="meter-sample-row"') == 2
        assert "cycle-123" in html
        assert "treatment" in html
        assert "sensor-1" in html
        assert "2026-07-07T00:00:00Z" in html
        assert "value: 42.0" in html

        assert "cycle-124" in html
        assert "control" in html
        assert "sensor-2" in html
        assert "2026-07-07T01:00:00Z" in html
        assert "value: 84.0" in html
        assert "samples-empty" not in html

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "/evolve/samples" in args[0]
        assert kwargs["params"] == {"limit": 50}
        from app.config import settings
        assert kwargs["timeout"] == settings.request_timeout


def test_get_index_failure():
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_get.side_effect = Exception("Connection timeout")

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert "samples-empty" in html
        assert "no samples yet" in html
        assert "meter-sample-row" not in html


def test_get_index_empty_envelope():
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"samples": []}
        mock_get.return_value = mock_resp

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert "samples-empty" in html
        assert "no samples yet" in html
        assert "meter-sample-row" not in html


