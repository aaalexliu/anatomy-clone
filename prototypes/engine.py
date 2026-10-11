"""Write emission.json and playback.json for one prototype.

Reads the catalog and the motion clips. Does not read label sets or the harness.
"""

from __future__ import annotations

import json
from pathlib import Path

from body.motion import required_moment_signs, sample_motion
from body.rig import BONES, COORDINATES, joint_positions, moment_arms, muscle_polylines

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"


def run_prototype(prototype_id: str, display_name: str, estimator: str, estimate) -> None:
    vocab = _read("exam/vocab.json")
    catalog = _read("exam/catalog.json")
    _guard_vocab(vocab)
    proto_dir = RUNS / prototype_id
    proto_dir.mkdir(parents=True, exist_ok=True)
    (proto_dir / "prototype.json").write_text(
        json.dumps({"id": prototype_id, "name": display_name, "estimator": estimator}, indent=2) + "\n"
    )
    for item in catalog["items"]:
        motion = _read(f"exam/motions/{item['motion']}.json")
        emission, playback = _simulate(prototype_id, estimator, item["id"], motion, estimate, vocab)
        out = proto_dir / item["id"]
        out.mkdir(parents=True, exist_ok=True)
        _write(out / "emission.json", emission)
        _write(out / "playback.json", playback)
        mid = len(emission["muscle_roles"]["roles"]) // 2
        names = emission["muscle_roles"]["names"]
        roles = emission["muscle_roles"]["roles"][mid]
        shown = [f"{role}:{name}" for name, role in zip(names, roles) if role != "inactive"]
        print(f"{prototype_id} {item['id']}: {', '.join(shown)}")


def _simulate(prototype_id, estimator, item_id, motion, estimate, vocab):
    times, rows = sample_motion(motion)
    required = required_moment_signs(motion)
    names = list(vocab["muscles"])
    role_rows = []
    score_rows = []
    frames = []
    confidences = []
    for time, angles in zip(times, rows):
        arms = moment_arms(angles)
        roles, scores, confidence = estimate(arms, required)
        confidences.append(confidence)
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
        "prototype_id": prototype_id,
        "item_id": item_id,
        "joint_angles": {
            "unit": "deg",
            "times_s": [round(time, 5) for time in times],
            "coordinates": list(COORDINATES),
            "values": [[round(row[name], 4) for name in COORDINATES] for row in rows],
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
            "skeleton": motion["skeleton"],
            "tracker": None,
            "estimator": estimator,
            "motion_source": motion["motion_source"],
            "drive_track_id": None,
        },
    }
    playback = {
        "prototype_id": prototype_id,
        "item_id": item_id,
        "fps": motion["fps"],
        "bones": [list(pair) for pair in BONES],
        "frames": frames,
    }
    return emission, playback


def _guard_vocab(vocab: dict) -> None:
    if list(vocab["coordinates"]) != list(COORDINATES):
        raise SystemExit("vocab coordinates do not match the rig")
    from body.rig import MUSCLES

    if list(vocab["muscles"]) != [muscle["name"] for muscle in MUSCLES]:
        raise SystemExit("vocab muscles do not match the rig")


def _read(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _point(value) -> list[float]:
    return [round(float(value[0]), 5), round(float(value[1]), 5), round(float(value[2]), 5)]
