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
            [sys.executable, str(self._script), "--input", str(input_path), "--output", str(output)],
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
            self.assertEqual(data["status"], "unclear")


if __name__ == "__main__":
    unittest.main()
