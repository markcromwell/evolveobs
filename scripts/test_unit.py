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
        def side_effect(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "/evolve/samples" in url:
                mock_resp.json.return_value = {"samples": mock_samples}
            elif "/evolve/cycles" in url:
                mock_resp.json.return_value = {"cycles": []}
            return mock_resp
        mock_get.side_effect = side_effect

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

        assert mock_get.call_count == 2
        # Verify first call (samples)
        args_s, kwargs_s = mock_get.call_args_list[0]
        assert "/evolve/samples" in args_s[0]
        assert kwargs_s["params"] == {"limit": 50}
        assert kwargs_s["timeout"] == 5.0
        
        # Verify second call (cycles)
        args_c, kwargs_c = mock_get.call_args_list[1]
        assert "/evolve/cycles" in args_c[0]
        assert kwargs_c["timeout"] == 5.0


def test_get_index_empty_envelope():
    with patch("app.routers.web.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"samples": [], "cycles": []}
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


def test_get_index_cycles_success():
    mock_cycles = [
        {
            "slice_index": 1,
            "slice_worked": 10,
            "story_done": True,
            "progress": "IMPROVING",
            "breaker_action": "CONTINUE",
            "is_seed": True,
        },
        {
            "slice_index": 2,
            "slice_worked": 5,
            "story_done": False,
            "progress": "STAGNANT",
            "breaker_action": "HALT",
            "is_seed": False,
        }
    ]
    with patch("app.routers.web.httpx.get") as mock_get:
        def side_effect(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "/evolve/samples" in url:
                mock_resp.json.return_value = {"samples": []}
            elif "/evolve/cycles" in url:
                mock_resp.json.return_value = {"cycles": mock_cycles}
            return mock_resp
        mock_get.side_effect = side_effect

        with patch("app.routers.web.settings") as mock_settings:
            mock_settings.x_api_key = "test-api-key"
            mock_settings.mcp_url = "http://mcp-test"

            resp = client.get("/")
            assert resp.status_code == 200
            html = resp.text

            # Verify cycles table is rendered
            assert html.count('data-testid="cycle-row"') == 2
            assert "cycles-empty" not in html

            # Verify cells contents
            assert "1" in html
            assert "10" in html
            assert "True" in html
            assert "IMPROVING" in html
            assert "CONTINUE" in html
            assert "seed-badge" in html
            assert "seed" in html

            assert "2" in html
            assert "5" in html
            assert "False" in html
            assert "STAGNANT" in html
            assert "HALT" in html

            assert html.count('data-testid="seed-badge"') == 1

            assert mock_get.call_count == 2
            args, kwargs = mock_get.call_args_list[1]
            assert "http://mcp-test/evolve/cycles" in args[0]
            assert kwargs["headers"] == {"X-API-Key": "test-api-key"}
            assert kwargs["timeout"] == 5.0


def test_get_index_cycles_failure_resilience():
    with patch("app.routers.web.httpx.get") as mock_get:
        def side_effect(url, *args, **kwargs):
            if "/evolve/samples" in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"samples": []}
                return mock_resp
            elif "/evolve/cycles" in url:
                raise Exception("Cycles endpoint down")
        mock_get.side_effect = side_effect

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text

        # Cycles should fall back to empty, displaying the empty div
        assert "cycles-empty" in html
        assert "no cycles yet" in html
        assert html.count('data-testid="cycle-row"') == 0

