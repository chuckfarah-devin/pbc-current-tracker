"""Parity tests for the /api/snorkel-conditions endpoint."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class SnorkelConditionsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_snorkel_conditions_returns_replay_payload(self):
        r = self.client.get("/api/snorkel-conditions")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["mode"], "recorded_replay")
        self.assertTrue(data["mode_disclaimer"])
        self.assertTrue(data["cameras"])
        self.assertTrue(data["water_appearance"])
        self.assertTrue(data["weather"])
        self.assertTrue(data["algae"])
        self.assertEqual(data["c16"]["info_url"], "https://www.sfwmd.gov/")

    def test_each_camera_has_provenance(self):
        r = self.client.get("/api/snorkel-conditions")
        data = r.json()
        for cam in data["cameras"]:
            self.assertIn("camera_id", cam)
            self.assertIn("location", cam)
            self.assertIn("status", cam)
            self.assertIn("age_minutes", cam)
            self.assertIn("local_conditions_verified", cam)

    def test_fixture_images_are_served(self):
        r = self.client.get("/api/snorkel-conditions")
        data = r.json()
        image_urls = [cam["image_url"] for cam in data["cameras"] if cam.get("image_url")]
        image_urls += [a["image_url"] for a in data["water_appearance"] if a.get("image_url")]
        for url in image_urls:
            img = self.client.get(url)
            self.assertEqual(img.status_code, 200, f"Image not reachable: {url}")
            self.assertTrue(img.headers.get("content-type", "").startswith("image/"))

    def test_recorded_water_appearance_is_framing_verified(self):
        r = self.client.get("/api/snorkel-conditions")
        data = r.json()
        for a in data["water_appearance"]:
            self.assertTrue(a["framing_verified"])

    def test_replay_sargassum_has_exact_period_dates_and_provenance(self):
        r = self.client.get("/api/snorkel-conditions")
        data = r.json()
        algae = data["algae"]
        self.assertIsNotNone(algae)
        self.assertIsNotNone(algae["period_start"])
        self.assertIsNotNone(algae["period_end"])
        self.assertEqual(algae["composite"], "7DAY")
        self.assertTrue(algae["nominal_resolution_m"])
        self.assertTrue(
            any("sargassum" in lim.lower() for lim in algae["limitations"])
        )

    def test_replay_limitations_use_sargassum_wording(self):
        r = self.client.get("/api/snorkel-conditions")
        data = r.json()
        self.assertTrue(
            any("Sargassum" in lim for lim in data["limitations"])
        )

    def test_appearance_failure_field_is_supported_without_affecting_other_sources(self):
        from app.models.snorkel_conditions import WaterAppearanceObservation
        appearance = WaterAppearanceObservation(
            camera_id="delray", location="Delray Beach", headline="Visual review only",
            status="framing_unverified", error="decode failed",
        )
        self.assertEqual(appearance.error, "decode failed")
        replay = self.client.get("/api/snorkel-conditions").json()
        self.assertTrue(replay["cameras"])
        self.assertTrue(replay["weather"])
        self.assertTrue(replay["algae"])
        self.assertTrue(replay["surface_motion"])

    def test_live_mode_is_reachable_without_fetching(self):
        """Live endpoint should be reachable when live-cache already exists."""
        with patch("app.routers.snorkel_conditions._start_refresh", new_callable=AsyncMock):
            r = self.client.get("/api/snorkel-conditions?mode=live")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["mode"], "live")
            self.assertTrue(data["cameras"])
            for a in data["water_appearance"]:
                self.assertFalse(a["framing_verified"])

    def test_live_mode_with_empty_cache_exposes_motion_unavailable(self):
        """An empty live cache must not return a null surface_motion object."""
        import app.routers.snorkel_conditions as sc
        with tempfile.TemporaryDirectory() as tmp:
            live_dir = Path(tmp)
            with patch.object(sc, "_live_dir", return_value=live_dir):
                r = self.client.get("/api/snorkel-conditions?mode=live")
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertEqual(data["mode"], "live")
                self.assertIsNotNone(data["surface_motion"])
                self.assertEqual(data["surface_motion"]["status"], "unable_to_assess")
                self.assertEqual(data["surface_motion"]["evidence_strength"], "unable")
                self.assertEqual(data["refresh_status"], "idle")

    def test_live_mode_while_refresh_running_exposes_motion_checking(self):
        """While a refresh is running, surface_motion should indicate checking."""
        import app.routers.snorkel_conditions as sc
        with tempfile.TemporaryDirectory() as tmp:
            live_dir = Path(tmp)

            class FakeTask:
                def done(self):
                    return False

                def cancel(self):
                    pass

            sc._refresh_task = FakeTask()
            try:
                with patch.object(sc, "_live_dir", return_value=live_dir):
                    r = self.client.get("/api/snorkel-conditions?mode=live")
                    self.assertEqual(r.status_code, 200)
                    data = r.json()
                    self.assertEqual(data["refresh_status"], "running")
                    self.assertIsNotNone(data["surface_motion"])
                    self.assertEqual(data["surface_motion"]["status"], "checking")
                    self.assertEqual(data["surface_motion"]["evidence_strength"], "pending")
            finally:
                sc._refresh_task = None


if __name__ == "__main__":
    unittest.main()
