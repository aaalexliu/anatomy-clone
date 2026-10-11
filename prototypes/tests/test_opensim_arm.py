"""arm26 moment arms have to come from a live OpenSim call."""

import unittest

from prototypes.opensim_arm.arm import HEADS, Arm26


class OpenSimArmTest(unittest.TestCase):
    def test_elbow_signs_match_the_model(self):
        muscles = list(HEADS) + ["brachioradialis", "gluteus_maximus"]
        arms, posed = Arm26().moment_arms(
            {"shoulder_flexion": 0.0, "elbow_flexion": 70.0},
            muscles,
        )
        self.assertAlmostEqual(posed["elbow_flexion"], 70.0, places=3)
        self.assertGreater(arms["biceps_brachii"]["elbow_flexion"], 0.01)
        self.assertGreater(arms["brachialis"]["elbow_flexion"], 0.005)
        self.assertLess(arms["triceps_brachii"]["elbow_flexion"], -0.005)
        self.assertGreater(arms["biceps_brachii"]["shoulder_flexion"], 0.0)
        self.assertLess(arms["triceps_brachii"]["shoulder_flexion"], 0.0)
        self.assertEqual(arms["gluteus_maximus"]["hip_flexion"], 0.0)
        self.assertEqual(arms["brachioradialis"]["elbow_flexion"], 0.0)


if __name__ == "__main__":
    unittest.main()
