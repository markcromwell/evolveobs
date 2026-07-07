# Unit tests for EVOLVE Observability. Uses the app factory for an isolated instance.
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import create_app

client = TestClient(create_app())


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


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
        
        # Verify row-count equals sample-count
        row_count = html.count('data-testid="meter-sample-row"')
        assert row_count == len(mock_samples)
        assert row_count > 0

        # Verify mutual exclusivity: when rows > 0, empty-state is not present
        assert "samples-empty" not in html
        assert "no samples yet" not in html

        assert "cycle-123" in html
        assert "treatment" in html
        assert "sensor-1" in html
        assert "2026-07-07T00:00:00Z" in html

        assert "cycle-124" in html
        assert "control" in html
        assert "sensor-2" in html
        assert "2026-07-07T01:00:00Z" in html

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "/evolve/samples" in args[0]
        assert kwargs["params"] == {"limit": 50}
        assert kwargs["timeout"] == 5.0


def test_get_index_empty_envelope():
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"samples": []}
        mock_get.return_value = mock_resp

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        
        # Verify row-count is 0
        assert html.count('data-testid="meter-sample-row"') == 0
        
        # Verify mutual exclusivity: when rows == 0, empty-state is present
        assert "samples-empty" in html
        assert "no samples yet" in html


def test_get_index_failure():
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_get.side_effect = Exception("Connection timeout")

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        
        # Verify row-count is 0
        assert html.count('data-testid="meter-sample-row"') == 0
        
        # Verify mutual exclusivity: when rows == 0, empty-state is present
        assert "samples-empty" in html
        assert "no samples yet" in html

