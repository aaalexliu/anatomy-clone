"""Drive every exam clip through arm26 and write the usual run files.

Joint angles are the scripted clip, clamped to the model and posed on
r_shoulder_elev / r_elbow_flex. Muscle roles use those OpenSim moment arms
and the same sign rule as the finite-difference prototype. Playback is the
toy stick figure in the scripted pose, colored by the OpenSim roles, so the
viewer can compare them in one camera.
"""

from __future__ import annotations

import json
from pathlib import Path

from body.motion import required_moment_signs, sample_motion
from body.rig import BONES, joint_positions, muscle_polylines
from prototypes.moment_arm.estimate import estimate
from prototypes.opensim_arm.arm import POSE, Arm26

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
PROTOTYPE_ID = "opensim_arm"
ESTIMATOR = "opensim_moment_arm"
POSED = tuple(POSE)


def main() -> None:
    vocab = json.loads((ROOT / "exam" / "vocab.json").read_text())
    catalog = json.loads((ROOT / "exam" / "catalog.json").read_text())
    names = list(vocab["muscles"])
    arm = Arm26()
    proto_dir = RUNS / PROTOTYPE_ID
    proto_dir.mkdir(parents=True, exist_ok=True)
    (proto_dir / "prototype.json").write_text(
        json.dumps(
            {
                "id": PROTOTYPE_ID,
                "name": "OpenSim arm26 moment arm",
                "estimator": ESTIMATOR,
            },
            indent=2,
        )
        + "\n"
    )
    for item in catalog["items"]:
        motion = json.loads((ROOT / "exam" / "motions" / f"{item['motion']}.json").read_text())
        emission, playback = _simulate(arm, names, item["id"], motion, vocab)
        out = proto_dir / item["id"]
        out.mkdir(parents=True, exist_ok=True)
        _write(out / "emission.json", emission)
        _write(out / "playback.json", playback)
        mid = len(emission["muscle_roles"]["roles"]) // 2
        shown = [
            f"{role}:{name}"
            for name, role in zip(names, emission["muscle_roles"]["roles"][mid])
            if role != "inactive"
        ]
        print(f"{PROTOTYPE_ID} {item['id']}: {', '.join(shown) or '(no working muscles)'}")


def _simulate(arm: Arm26, names: list[str], item_id: str, motion: dict, vocab: dict):
    times, rows = sample_motion(motion)
    required = required_moment_signs(motion)
    role_rows = []
    score_rows = []
    frames = []
    confidences = []
    posed_rows = []
    for time, angles in zip(times, rows):
        arms, posed = arm.moment_arms(angles, names)
        roles, scores, confidence = estimate(arms, required)
        confidences.append(confidence)
        posed_rows.append([round(posed[name], 4) for name in POSED])
        role_rows.append([roles[name] for name in names])
        score_rows.append([round(float(scores[name]), 6) for name in names])
        joints = joint_positions(angles)
        lines = muscle_polylines(angles)
        frames.append(
            {
                "t": round(time, 5),
                "joints": {name: _point(joints[name]) for name in vocab["joints"]},
                "muscles": {
                    name: {"role": roles[name], "polyline": [_point(p) for p in lines[name]]}
                    for name in names
                },
            }
        )
    emission = {
        "prototype_id": PROTOTYPE_ID,
        "item_id": item_id,
        "joint_angles": {
            "unit": "deg",
            "times_s": [round(time, 5) for time in times],
            "coordinates": list(POSED),
            "values": posed_rows,
        },
        "muscle_roles": {
            "times_s": [round(time, 5) for time in times],
            "names": names,
            "roles": role_rows,
            "scores": score_rows,
        },
        "load": {
            "description": motion["load"]["description"],
            "direction_known": bool(motion["load"]["direction_known"]),
        },
        "confidence": round(sum(confidences) / len(confidences), 4),
        "provenance": {
            "skeleton": "arm26",
            "tracker": None,
            "estimator": ESTIMATOR,
            "motion_source": motion["motion_source"],
            "drive_track_id": None,
        },
    }
    playback = {
        "prototype_id": PROTOTYPE_ID,
        "item_id": item_id,
        "fps": motion["fps"],
        "bones": [list(pair) for pair in BONES],
        "frames": frames,
    }
    return emission, playback


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _point(value) -> list[float]:
    return [round(float(value[0]), 5), round(float(value[1]), 5), round(float(value[2]), 5)]


if __name__ == "__main__":
    main()
