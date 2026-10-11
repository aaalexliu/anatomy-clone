"""The harness grades emissions. It does not call a prototype."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness.score import score_runs

ROOT = Path(__file__).resolve().parents[2]
BANNED = {"prototypes", "body"}


class IsolationTest(unittest.TestCase):
    def test_harness_does_not_import_prototypes(self):
        for path in (ROOT / "harness").rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    top = module.split(".")[0]
                    self.assertNotIn(top, BANNED, f"{path} imports {module}")

    def test_scorer_source_does_not_mention_playback(self):
        text = (ROOT / "harness" / "score.py").read_text()
        self.assertNotIn("playback", text)

    def test_score_runs_does_not_open_playback(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "moment_arm" / "biceps_flexion"
            run.mkdir(parents=True)
            emission = _passing_biceps()
            (run / "emission.json").write_text(json.dumps(emission))
            (run / "playback.json").write_text('{"joints": "this file must not be read"}')
            opened = []
            real_read = Path.read_text

            def spy(self, *args, **kwargs):
                opened.append(str(self))
                return real_read(self, *args, **kwargs)

            with mock.patch.object(Path, "read_text", spy):
                score_runs(Path(tmp), ROOT / "exam")
            playbacks = [name for name in opened if name.endswith("playback.json")]
            self.assertEqual(playbacks, [])
            score = json.loads((run / "score.json").read_text())
            self.assertEqual(score["muscle_role"]["status"], "pass")
            self.assertNotEqual(score["overall"]["status"], "invalid")


def _passing_biceps():
    names = [
        "biceps_brachii",
        "brachialis",
        "brachioradialis",
        "triceps_brachii",
        "anterior_deltoid",
        "posterior_deltoid",
        "gluteus_maximus",
        "biceps_femoris",
        "vastus_lateralis",
        "iliopsoas",
    ]
    roles = {name: "inactive" for name in names}
    roles["biceps_brachii"] = "prime_mover"
    roles["brachialis"] = "prime_mover"
    roles["brachioradialis"] = "synergist"
    roles["triceps_brachii"] = "antagonist"
    scores = {name: 0.0 for name in names}
    scores["biceps_brachii"] = 0.9
    scores["brachialis"] = 0.8
    scores["brachioradialis"] = 0.4
    scores["triceps_brachii"] = 0.5
    coords = ["hip_flexion", "knee_flexion", "shoulder_flexion", "elbow_flexion"]
    return {
        "prototype_id": "moment_arm",
        "item_id": "biceps_flexion",
        "joint_angles": {
            "unit": "deg",
            "times_s": [0.0, 0.5, 1.0],
            "coordinates": coords,
            "values": [[0, 5, 0, 20], [0, 5, 0, 70], [0, 5, 0, 120]],
        },
        "muscle_roles": {
            "times_s": [0.0, 0.5, 1.0],
            "names": names,
            "roles": [[roles[name] for name in names] for _ in range(3)],
            "scores": [[scores[name] for name in names] for _ in range(3)],
        },
        "load": {"description": "No external load.", "direction_known": True},
        "confidence": 0.5,
        "provenance": {
            "skeleton": "toy_sagittal_v1",
            "tracker": None,
            "estimator": "fixture",
            "motion_source": "scripted_isolate",
            "drive_track_id": None,
        },
    }


if __name__ == "__main__":
    unittest.main()
