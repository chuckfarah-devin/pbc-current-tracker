"""Sanity tests for the Delray surface-flow PoC."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    import cv2
    import numpy as np
    HAS_CV = True
except ImportError:
    HAS_CV = False


class SurfaceFlowPocTests(unittest.TestCase):
    @property
    def _script(self) -> Path:
        return Path(__file__).parent.parent / "poc" / "delray_surface_flow_poc.py"

    @property
    def _reference_clip(self) -> Path:
        return Path(__file__).parent.parent / "poc" / "fixtures" / "delray-northward-example1.mp4"

    def _run(self, input_path: Path, output: Path) -> dict:
        r = subprocess.run(
            [sys.executable, str(self._script), "--input", str(input_path), "--output", str(output),
             "--retrieved-at", "2026-09-17T14:32:00+00:00", "--acquisition-id", "test-acquisition",
             "--minimum-duration", "10"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        return json.loads(r.stdout)

    def test_reference_clip_classifies_northward(self):
        if not HAS_CV:
            self.skipTest("OpenCV / NumPy not available")
        if not self._reference_clip.exists():
            self.skipTest("Reference fixture not present")
        with TemporaryDirectory() as td:
            out = Path(td) / "flow"
            data = self._run(self._reference_clip, out)
            self.assertEqual(data["status"], "likely_northward")
            self.assertTrue(data.get("framing_verified"))
            self.assertIn("likely northward", data.get("user_label", "").lower())
            self.assertIn("not a measured current", data.get("interpretation", "").lower())

    def test_unclear_for_static_input(self):
        if not HAS_CV:
            self.skipTest("OpenCV / NumPy not available")
        # A 2-frame black video should be rejected for low texture/weak motion.
        with TemporaryDirectory() as td:
            video_path = Path(td) / "black.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(video_path), fourcc, 5.0, (1280, 526))
            for _ in range(2):
                writer.write(np.zeros((526, 1280, 3), dtype=np.uint8))
            writer.release()
            if not video_path.exists() or video_path.stat().st_size == 0:
                self.skipTest("Could not write test video")
            out = Path(td) / "flow"
            data = self._run(video_path, out)
            self.assertEqual(data["status"], "unable_to_assess")
            self.assertIsNone(data["observed_at"])
            self.assertEqual(data["retrieved_at"], "2026-09-17T14:32:00+00:00")

    def test_zero_motion_is_neutral_and_weak_consistent_motion_can_be_possible(self):
        if not HAS_CV:
            self.skipTest("OpenCV / NumPy not available")
        import importlib.util
        spec = importlib.util.spec_from_file_location("flow", self._script)
        flow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flow)
        neutral = {name: {"usable": True, "median_dx_normalized_px_per_second": 0.01,
            "noise_floor_normalized_px_per_second": 0.05, "leftward_agreement": 0.0,
            "rightward_agreement": 0.0, "window_medians": [0.01, 0.01], "pair_count": 20}
            for name in flow.BASE_REGIONS}
        self.assertEqual(flow.classify(neutral, {})["status"], "no_clear_directional_motion")
        weak = {name: {**value, "median_dx_normalized_px_per_second": -0.08,
            "leftward_agreement": 0.70, "window_medians": [-0.08, -0.07]}
            for name, value in neutral.items()}
        result = flow.classify(weak, {})
        self.assertEqual(result["status"], "possible_northward")
        south = {name: {**value, "median_dx_normalized_px_per_second": 0.08,
            "rightward_agreement": 0.70, "window_medians": [0.08, 0.07]}
            for name, value in neutral.items()}
        self.assertEqual(flow.classify(south, {})["status"], "possible_southward")
        mixed = dict(weak)
        mixed["Reflection edge"] = south["Reflection edge"]
        self.assertEqual(flow.classify(mixed, {})["status"], "motion_detected_direction_mixed")

    def test_stale_or_mismatched_delray_clip_is_ineligible(self):
        from app.routers.snorkel_conditions import _eligible_delray_motion
        with TemporaryDirectory() as td:
            clip = Path(td) / "delray.ts"
            clip.write_bytes(b"current acquisition")
            other_camera = {"id": "boynton", "status": "available", "acquisition_id": "anything"}
            self.assertFalse(_eligible_delray_motion(other_camera, clip)[0])
            stale = {"id": "delray", "status": "stream_advancing_capture_unverified", "acquisition_id": "old-hash"}
            ok, reason = _eligible_delray_motion(stale, clip)
            self.assertFalse(ok)
            self.assertIn("hash", reason)


if __name__ == "__main__":
    unittest.main()
