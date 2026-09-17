"""Unit tests for the bounded USF sargassum search."""
import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.routers.snorkel_conditions import _discover_latest_sargassum


class SargassumSearchTests(unittest.TestCase):
    @staticmethod
    def _write_dummy_result(out: Path, period_end: str) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(
            json.dumps({"source": {"period_end": period_end}}), encoding="utf-8"
        )

    @patch("app.routers.snorkel_conditions._run_poc")
    def test_selects_closest_valid_composite(self, mock_run):
        today = date.today()

        def side_effect(script, args, timeout):
            out = Path(args[args.index("--output") + 1])
            day = out.name
            if day in (
                today.isoformat(),
                (today - timedelta(days=1)).isoformat(),
            ):
                return False, "no product"
            if day == (today - timedelta(days=2)).isoformat():
                self._write_dummy_result(out, day)
                return True, "ok"
            return False, "no product"

        mock_run.side_effect = side_effect
        with TemporaryDirectory() as td:
            ok, msg = _discover_latest_sargassum(Path(td), max_lookback=5)
            self.assertTrue(ok)
            self.assertIn((today - timedelta(days=2)).isoformat(), msg)


    @patch("app.routers.snorkel_conditions._run_poc")
    def test_reports_failure_when_no_composite_in_bound(self, mock_run):
        def side_effect(script, args, timeout):
            return False, "no product"

        mock_run.side_effect = side_effect
        with TemporaryDirectory() as td:
            ok, msg = _discover_latest_sargassum(Path(td), max_lookback=3)
            self.assertFalse(ok)
            self.assertIn("last 3 days", msg)

    @patch("app.routers.snorkel_conditions._run_poc")
    def test_does_not_reference_historical_demo(self, mock_run):
        def side_effect(script, args, timeout):
            return False, "no product"

        mock_run.side_effect = side_effect
        with TemporaryDirectory() as td:
            ok, msg = _discover_latest_sargassum(Path(td), max_lookback=2)
            self.assertFalse(ok)
            self.assertNotIn("demo", msg.lower())


if __name__ == "__main__":
    unittest.main()
