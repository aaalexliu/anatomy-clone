"""The reference body is not allowed to grade itself, and the meshes parse."""

import ast
import unittest
from pathlib import Path

from body.meshes import read_vtp
from body.shoulder_load import MOBL_PATH, external_rotation_sign, required_signs

ROOT = Path(__file__).resolve().parents[2]


class ReferenceBodyTest(unittest.TestCase):
    def test_humerus_mesh_is_a_closed_surface(self):
        vertices, indices = read_vtp(ROOT / "models" / "opensim" / "Geometry" / "humerus_rv.vtp")
        self.assertGreater(len(vertices), 100)
        self.assertGreater(len(indices), 300)
        self.assertEqual(len(indices) % 3, 0)

    def test_external_rotation_sign_makes_infraspinatus_an_agonist(self):
        import opensim

        from prototypes.moment_arm.estimate import estimate

        sign = external_rotation_sign(MOBL_PATH)
        self.assertIn(sign, (1, -1))
        opensim.Logger.setLevelString("Off")
        model = opensim.Model(str(MOBL_PATH))
        state = model.initSystem()
        coords = model.getCoordinateSet()
        for name, degrees in (("elbow_flexion", 90.0), ("elv_angle", 0.0), ("shoulder_elv", 0.0), ("shoulder_rot", 0.0)):
            coord = coords.get(name)
            coord.setValue(state, __import__("math").radians(degrees))
        model.realizePosition(state)
        arms = {}
        for name in ("INFSP", "TMIN", "DELT3", "SUBSC"):
            muscle = model.getMuscles().get(name)
            arms[name] = {
                "shoulder_rot": float(muscle.computeMomentArm(state, coords.get("shoulder_rot"))),
                "elv_angle": 0.0,
                "shoulder_elv": 0.0,
                "elbow_flexion": 0.0,
            }
        roles, _, _ = estimate(arms, required_signs(sign))
        self.assertEqual(roles["INFSP"], "prime_mover")
        self.assertIn(roles["SUBSC"], ("antagonist", "inactive"))
        self.assertNotEqual(roles["SUBSC"], "prime_mover")

    def test_default_infraspinatus_sits_on_the_shoulder(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "build_reference_body", ROOT / "scripts" / "build_reference_body.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        frame = module._default_frame("left")
        muscle = frame["muscles"]["INFSP"]
        self.assertEqual(muscle["role"], "prime_mover")
        self.assertNotEqual(frame["muscles"]["SUBSC"]["role"], "prime_mover")
        matrix = frame["bodies"]["humerus_l"]
        shoulder = (matrix[12], matrix[13], matrix[14])
        for point in muscle["polyline"]:
            distance = sum((point[i] - shoulder[i]) ** 2 for i in range(3)) ** 0.5
            self.assertLess(distance, 0.16, point)
        self.assertGreater(min(point[1] for point in muscle["polyline"]), 1.2)

    def test_a_straight_arm_does_not_pass_the_motion_gate(self):
        import importlib.util

        import numpy as np

        spec = importlib.util.spec_from_file_location(
            "build_reference_body", ROOT / "scripts" / "build_reference_body.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = []
        for index in range(24):
            row = {"t": index / 6}
            points = {
                "shoulder_l": np.array([0.0, 0.5, -0.2]),
                "shoulder_r": np.array([0.0, 0.5, 0.2]),
                "hip_l": np.array([0.0, 0.0, -0.1]),
                "hip_r": np.array([0.0, 0.0, 0.1]),
                "elbow_l": np.array([0.0, 0.25, -0.2]),
                "elbow_r": np.array([0.0, 0.25, 0.2]),
                "wrist_l": np.array([0.0, 0.05, -0.2]),
                "wrist_r": np.array([0.0, 0.05, 0.2]),
            }
            for name, point in points.items():
                row[name] = {"p": point, "v": 1.0}
            rows.append(row)
        held, fraction, counted = module._flexion_fraction(rows, "left")
        self.assertFalse(held)
        self.assertLess(fraction, 0.6)
        self.assertGreaterEqual(counted, 12)
        for row in rows:
            row["wrist_l"] = {"p": np.array([0.25, 0.25, -0.2]), "v": 1.0}
        held, fraction, _counted = module._flexion_fraction(rows, "left")
        self.assertTrue(held)
        self.assertGreaterEqual(fraction, 0.6)

    def test_reference_script_does_not_score(self):
        path = ROOT / "scripts" / "build_reference_body.py"
        text = path.read_text()
        tree = ast.parse(text)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        for module in modules:
            self.assertNotEqual(module.split(".")[0], "harness")
        self.assertNotIn("score.json", text)
        self.assertNotIn("score_spec", text)


if __name__ == "__main__":
    unittest.main()
