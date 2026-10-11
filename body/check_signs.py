"""Developer check: finite-difference signs vs the frozen action table.

This is not the harness. Prototypes do not call it when they assign roles.
Each muscle is checked at a pose where that joint is in mid range.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from body.rig import moment_arms

ROOT = Path(__file__).resolve().parents[1]
POSES = {
    "sagittal": {
        "hip_flexion": 40,
        "knee_flexion": 50,
        "shoulder_flexion": 30,
        "elbow_flexion": 70,
    },
    "cuff": {
        "shoulder_abduction": 40,
        "shoulder_external_rotation": 20,
        "elbow_flexion": 60,
    },
    "elevated": {
        "shoulder_abduction": 80,
        "shoulder_horizontal_abduction": 20,
        "shoulder_external_rotation": 15,
        "elbow_flexion": 90,
        "scapular_retraction": 15,
    },
    "overhead": {
        "shoulder_abduction": 120,
        "shoulder_flexion": 20,
        "elbow_flexion": 40,
        "shoulder_external_rotation": 10,
    },
}
# muscle -> pose. Unlisted muscles use sagittal.
POSE_FOR = {
    "infraspinatus": "cuff",
    "teres_minor": "cuff",
    "subscapularis": "cuff",
    "supraspinatus": "cuff",
    "middle_trapezius": "elevated",
    "lower_trapezius": "elevated",
    "rhomboid_major": "elevated",
    "latissimus_dorsi": "elevated",
    "pectoralis_major": "elevated",
    "supraspinatus": "low",
}
POSES["low"] = {"shoulder_abduction": 25, "elbow_flexion": 20}
ACTION_POSE = {
    ("posterior_deltoid", "shoulder_horizontal_abduction"): "elevated",
}
MIN_ARM = 0.004


def main() -> int:
    table = json.loads((ROOT / "exam" / "action_table.json").read_text())
    bad = []
    cache = {name: moment_arms(pose) for name, pose in POSES.items()}
    for muscle, expect in table["muscles"].items():
        bits = []
        for coord, sign in expect.items():
            pose_name = ACTION_POSE.get((muscle, coord), POSE_FOR.get(muscle, "sagittal"))
            value = cache[pose_name][muscle][coord]
            ok = value * sign > MIN_ARM
            bits.append(f"{pose_name}:{coord}={value:+.4f}{' ok' if ok else ' BAD'}")
            if not ok:
                bad.append(f"{pose_name} {muscle} {coord} got {value:+.4f} want sign {sign}")
        print(f"{muscle:22} {', '.join(bits)}")
    if bad:
        print("SIGN MISMATCH")
        for row in bad:
            print(" ", row)
        return 1
    print("signs match the action table")
    return 0


if __name__ == "__main__":
    main()
