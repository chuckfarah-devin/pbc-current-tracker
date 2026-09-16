"""Parity tests for the /api/snorkel-conditions endpoint."""
import unittest
from unittest.mock import patch

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

    def test_live_mode_is_reachable_without_fetching(self):
        """Live endpoint should be reachable when live-cache already exists."""
        with patch(
            "app.routers.snorkel_conditions._update_live_sources",
            return_value={
                "camera": (True, ""),
                "appearance": (True, ""),
                "weather": (True, ""),
                "sargassum": (True, ""),
            },
        ):
            r = self.client.get("/api/snorkel-conditions?mode=live")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["mode"], "live")
            self.assertTrue(data["cameras"])
            for a in data["water_appearance"]:
                self.assertFalse(a["framing_verified"])


if __name__ == "__main__":
    unittest.main()
