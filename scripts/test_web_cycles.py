# Test suite for EVOLVE Observability cycle rendering.
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Ensure scripts directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_unit import client


def test_cycles_render_non_empty():
    mock_cycles = [
        # Normal cycle
        {
            "slice_index": 1,
            "slice_worked": "PASS",
            "story_done": "PASS",
            "progress": "IMPROVING",
            "breaker_action": "CONTINUE",
            "layer_fidelity": "PASS",
            "layer_executable_acceptance": "PASS",
            "layer_negative_tests": "PASS",
            "layer_runtime_probe": "PASS",
            "layer_hollow_probe": "PASS",
            "evidence_refs": ["ref-123", "ref-456"],
            "is_seed": False,
        },
        # Seed cycle
        {
            "slice_index": 2,
            "slice_worked": "FAIL",
            "story_done": "FAIL",
            "progress": "STALLED",
            "breaker_action": "HALT_ROLLBACK_ESCALATE",
            "layer_fidelity": None,
            "layer_executable_acceptance": None,
            "layer_negative_tests": "FAIL",
            "layer_runtime_probe": "UNKNOWN",
            "layer_hollow_probe": "UNKNOWN",
            "evidence_refs": ["ref-seed-xyz"],
            "is_seed": True,
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

        resp = client.get("/")
        assert resp.status_code == 200
        soup = BeautifulSoup(resp.text, "html.parser")

        # Verify cycles-empty is not present
        assert soup.find(attrs={"data-testid": "cycles-empty"}) is None

        rows = soup.find_all(attrs={"data-testid": "cycle-row"})
        assert len(rows) == 2

        # Assertions for Normal cycle (row 1)
        r1 = rows[0]
        # Check all 5 done spans are present and correct
        fid1 = r1.find(attrs={"data-testid": "done-layer-fidelity"})
        assert fid1 is not None and fid1.text.strip() == "PASS"

        exe1 = r1.find(attrs={"data-testid": "done-layer-executable_acceptance"})
        assert exe1 is not None and exe1.text.strip() == "PASS"

        neg1 = r1.find(attrs={"data-testid": "done-layer-negative_tests"})
        assert neg1 is not None and neg1.text.strip() == "PASS"

        run1 = r1.find(attrs={"data-testid": "done-layer-runtime_probe"})
        assert run1 is not None and run1.text.strip() == "PASS"

        hol1 = r1.find(attrs={"data-testid": "done-layer-hollow_probe"})
        assert hol1 is not None and hol1.text.strip() == "PASS"

        # Check evidence refs
        assert "ref-123" in r1.text and "ref-456" in r1.text
        # No seed badge
        assert r1.find(attrs={"data-testid": "seed-badge"}) is None

        # Assertions for Seed cycle (row 2)
        r2 = rows[1]
        fid2 = r2.find(attrs={"data-testid": "done-layer-fidelity"})
        # coerced from None to UNKNOWN
        assert fid2 is not None and fid2.text.strip() == "UNKNOWN"

        exe2 = r2.find(attrs={"data-testid": "done-layer-executable_acceptance"})
        # coerced from None to UNKNOWN
        assert exe2 is not None and exe2.text.strip() == "UNKNOWN"

        neg2 = r2.find(attrs={"data-testid": "done-layer-negative_tests"})
        assert neg2 is not None and neg2.text.strip() == "FAIL"

        run2 = r2.find(attrs={"data-testid": "done-layer-runtime_probe"})
        assert run2 is not None and run2.text.strip() == "UNKNOWN"

        hol2 = r2.find(attrs={"data-testid": "done-layer-hollow_probe"})
        assert hol2 is not None and hol2.text.strip() == "UNKNOWN"

        # Check evidence refs
        assert "ref-seed-xyz" in r2.text
        # Seed badge must be present
        seed_badge = r2.find(attrs={"data-testid": "seed-badge"})
        assert seed_badge is not None and seed_badge.text.strip() == "seed"


def test_cycles_render_empty():
    with patch("app.routers.web.httpx.get") as mock_get:
        def side_effect(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "/evolve/samples" in url:
                mock_resp.json.return_value = {"samples": []}
            elif "/evolve/cycles" in url:
                mock_resp.json.return_value = {"cycles": []}
            return mock_resp
        mock_get.side_effect = side_effect

        resp = client.get("/")
        assert resp.status_code == 200
        soup = BeautifulSoup(resp.text, "html.parser")

        # Verify cycles-empty is present
        empty_marker = soup.find(attrs={"data-testid": "cycles-empty"})
        assert empty_marker is not None
        assert "no cycles yet" in empty_marker.text

        # Verify no rows
        assert len(soup.find_all(attrs={"data-testid": "cycle-row"})) == 0
        # Verify no done-layer spans
        assert len(soup.find_all(attrs={"data-testid": lambda x: x and x.startswith("done-layer-")})) == 0
