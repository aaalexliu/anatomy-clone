"""Gates for legality, joint path, muscle role, and the negative control."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from harness.score import score_emission
from harness.tests.test_isolation import _passing_biceps

ROOT = Path(__file__).resolve().parents[2]


def _exam():
    exam = ROOT / "exam"
    spec = {item["id"]: item for item in json.loads((exam / "score_spec.json").read_text())["items"]}
    gates = json.loads((exam / "gates.json").read_text())
    action = json.loads((exam / "action_table.json").read_text())
    limits = {}
    for path in (exam / "limits").glob("*.json"):
        payload = json.loads(path.read_text())
        limits[payload["skeleton"]] = payload
    labels = {path.stem: json.loads(path.read_text()) for path in (exam / "labels").glob("*.json")}
    return spec, gates, action, limits, labels


def _heldout(track_id, values, visible=None, mirror=False, cropped=False):
    coords = ["hip_flexion", "knee_flexion", "shoulder_flexion", "elbow_flexion"]
    payload = {
        "track_id": track_id,
        "unit": "deg",
        "times_s": [0.0, 0.5, 1.0],
        "coordinates": coords,
        "values": values,
        "mirror": mirror,
        "cropped": cropped,
    }
    if visible is not None:
        payload["visible"] = visible
    return payload


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.spec, self.gates, self.action, self.limits, self.labels = _exam()

    def _score(self, emission, item_id, heldout=None):
        return score_emission(
            emission,
            spec=self.spec[item_id],
            labels=self.labels[self.spec[item_id]["label_set"]],
            action=self.action,
            limits=self.limits,
            gates=self.gates,
            heldout=heldout,
        )

    def test_no_heldout_track_abstains_joint_path(self):
        score = self._score(_passing_biceps(), "biceps_flexion", None)
        self.assertEqual(score["joint_path"]["status"], "abstain")
        self.assertIn("No held-out track", score["joint_path"]["reason"])
        self.assertEqual(score["overall"]["status"], "pass")

    def test_matching_drive_track_is_invalid_not_a_pass(self):
        emission = _passing_biceps()
        emission["provenance"]["drive_track_id"] = "person-squat-a"
        values = emission["joint_angles"]["values"]
        score = self._score(emission, "biceps_flexion", _heldout("person-squat-a", values))
        self.assertEqual(score["joint_path"]["status"], "invalid")
        self.assertNotEqual(score["joint_path"]["status"], "pass")
        self.assertNotEqual(score["overall"]["status"], "pass")
        self.assertEqual(score["overall"]["status"], "invalid")

    def test_different_track_with_small_error_passes(self):
        emission = _passing_biceps()
        emission["provenance"]["drive_track_id"] = "drive-1"
        values = [[0, 6, 0, 22], [0, 6, 1, 74], [0, 4, 0, 118]]
        score = self._score(emission, "biceps_flexion", _heldout("heldout-2", values))
        self.assertEqual(score["joint_path"]["status"], "pass")

    def test_large_joint_error_fails(self):
        emission = _passing_biceps()
        emission["provenance"]["drive_track_id"] = "drive-1"
        values = [[0, 40, 0, 20], [0, 40, 0, 70], [0, 40, 0, 120]]
        score = self._score(emission, "biceps_flexion", _heldout("heldout-2", values))
        self.assertEqual(score["joint_path"]["status"], "fail")
        self.assertEqual(score["overall"]["status"], "fail")

    def test_low_visibility_abstains(self):
        emission = _passing_biceps()
        emission["provenance"]["drive_track_id"] = "drive-1"
        visible = {
            "hip_flexion": False,
            "knee_flexion": False,
            "shoulder_flexion": True,
            "elbow_flexion": True,
        }
        score = self._score(
            emission,
            "biceps_flexion",
            _heldout("heldout-2", emission["joint_angles"]["values"], visible=visible),
        )
        self.assertEqual(score["joint_path"]["status"], "abstain")

    def test_mirror_abstains(self):
        emission = _passing_biceps()
        emission["provenance"]["drive_track_id"] = "drive-1"
        held = _heldout("heldout-2", emission["joint_angles"]["values"], mirror=True)
        score = self._score(emission, "biceps_flexion", held)
        self.assertEqual(score["joint_path"]["status"], "abstain")

    def test_angle_outside_limit_fails(self):
        emission = _passing_biceps()
        emission["joint_angles"]["values"][1][3] = 170
        score = self._score(emission, "biceps_flexion", None)
        self.assertEqual(score["legality"]["status"], "fail")
        self.assertEqual(score["overall"]["status"], "fail")

    def test_unknown_skeleton_abstains_legality(self):
        emission = _passing_biceps()
        emission["provenance"]["skeleton"] = "no-such-skeleton"
        score = self._score(emission, "biceps_flexion", None)
        self.assertEqual(score["legality"]["status"], "abstain")

    def test_wrong_prime_mover_sign_fails(self):
        emission = _passing_biceps()
        names = emission["muscle_roles"]["names"]
        roles = ["inactive"] * len(names)
        roles[names.index("triceps_brachii")] = "prime_mover"
        emission["muscle_roles"]["roles"] = [roles for _ in range(3)]
        score = self._score(emission, "biceps_flexion", None)
        self.assertEqual(score["muscle_role"]["status"], "fail")
        self.assertTrue(score["muscle_role"]["sign_violations"])

    def test_negative_control_passes_only_when_muscle_role_fails(self):
        emission = _passing_biceps()
        emission["item_id"] = "elbow_extension_as_biceps_curl"
        names = emission["muscle_roles"]["names"]
        roles = ["inactive"] * len(names)
        roles[names.index("triceps_brachii")] = "prime_mover"
        emission["muscle_roles"]["roles"] = [roles for _ in range(3)]
        failed = self._score(emission, "elbow_extension_as_biceps_curl", None)
        self.assertEqual(failed["muscle_role"]["status"], "fail")
        self.assertEqual(failed["negative_control"]["status"], "pass")
        self.assertEqual(failed["overall"]["status"], "pass")

        agreed = deepcopy(emission)
        roles = ["inactive"] * len(names)
        roles[names.index("biceps_brachii")] = "prime_mover"
        roles[names.index("brachialis")] = "prime_mover"
        roles[names.index("brachioradialis")] = "synergist"
        agreed["muscle_roles"]["roles"] = [roles for _ in range(3)]
        passed = self._score(agreed, "elbow_extension_as_biceps_curl", None)
        self.assertEqual(passed["muscle_role"]["status"], "pass")
        self.assertEqual(passed["negative_control"]["status"], "fail")
        self.assertEqual(passed["overall"]["status"], "fail")

    def test_unknown_load_direction_abstains_muscle_role(self):
        emission = _passing_biceps()
        emission["load"]["direction_known"] = False
        score = self._score(emission, "biceps_flexion", None)
        self.assertEqual(score["muscle_role"]["status"], "abstain")
        self.assertEqual(score["overall"]["status"], "abstain")


if __name__ == "__main__":
    unittest.main()
