"""Pose Rajagopal2016 from the reference clip and color MoBL-ARMS muscles.

The clip stays outside the repo. Joint angles come from OpenSim's CPU
inverse kinematics on MediaPipe Pose Landmarker landmarks (CPU, not a
PyTorch tracker). Muscle roles use computeMomentArm and the shared sign
rule. This script writes a playback file and does not write a score.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from body.meshes import load_body_meshes
from body.shoulder_load import (
    LABELS,
    LOAD_COORDINATES,
    PARENT_TO_RAJ,
    SHOULDER_MUSCLES,
    external_rotation_sign,
    required_signs,
)
from prototypes.moment_arm.estimate import estimate

RAJ_PATH = ROOT / "models" / "opensim" / "Rajagopal2016.osim"
GEOM_DIR = ROOT / "models" / "opensim" / "Geometry"
MOBL_PATH = ROOT / "models" / "opensim" / "MOBL_ARMS_41.osim"
OUT_DIR = ROOT / "viewer" / "public" / "reference"

# MediaPipe pose indices. Left and right are the person's, not the camera's.
LANDMARKS = {
    "shoulder_l": 11,
    "shoulder_r": 12,
    "elbow_l": 13,
    "elbow_r": 14,
    "wrist_l": 15,
    "wrist_r": 16,
    "hip_l": 23,
    "hip_r": 24,
    "knee_l": 25,
    "knee_r": 26,
    "ankle_l": 27,
    "ankle_r": 28,
}

# First minute is one figure. After that the clip cuts to split screens.
CLIP_SECONDS = 56.0
FPS = 6
MIN_VISIBILITY = 0.5
HOLD_GAP_S = 0.4

RAJ_MARKERS = {
    "shoulder_l": "humerus_l",
    "shoulder_r": "humerus_r",
    "elbow_l": "ulna_l",
    "elbow_r": "ulna_r",
    "wrist_l": "hand_l",
    "wrist_r": "hand_r",
    "hip_l": "femur_l",
    "hip_r": "femur_r",
}

LOCK_ALWAYS = (
    "knee_angle_r_beta",
    "knee_angle_l_beta",
    "subtalar_angle_r",
    "subtalar_angle_l",
    "mtp_angle_r",
    "mtp_angle_l",
    "wrist_flex_r",
    "wrist_flex_l",
    "wrist_dev_r",
    "wrist_dev_l",
    "pro_sup_r",
    "pro_sup_l",
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_body()
    motion = _exercise_motion()
    _write(OUT_DIR / "playback.json", motion)
    print(
        f"wrote {OUT_DIR / 'playback.json'} playable={motion['playable']} "
        f"frames={len(motion['frames'])} side={motion.get('working_side')}"
    )


def _write_body() -> None:
    meshes = load_body_meshes(RAJ_PATH, GEOM_DIR)
    payload = {
        "model": "Rajagopal2016",
        "units": "m",
        "meshes": [
            {
                "body": mesh["body"],
                "vertices": [[round(v, 5) for v in point] for point in mesh["vertices"]],
                "indices": mesh["indices"],
            }
            for mesh in meshes
        ],
    }
    _write(OUT_DIR / "body.json", payload)
    print(f"wrote {OUT_DIR / 'body.json'} ({len(meshes)} meshes)")


def _track(video: Path, task: Path) -> dict:
    if not task.is_file():
        raise SystemExit(f"Pose landmarker task not found: {task}")
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from PIL import Image

    tmp = Path(tempfile.mkdtemp(prefix="ref-frames-"))
    try:
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-t",
                str(CLIP_SECONDS),
                "-vf",
                f"fps={FPS}",
                str(tmp / "f_%04d.jpg"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        frames = sorted(tmp.glob("f_*.jpg"))
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(task)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.35,
            min_pose_presence_confidence=0.35,
            min_tracking_confidence=0.35,
        )
        landmarker = vision.PoseLandmarker.create_from_options(options)
        rows = []
        for index, path in enumerate(frames):
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(Image.open(path).convert("RGB")))
            result = landmarker.detect_for_video(image, int(round(index * 1000 / FPS)))
            rows.append(_read_pose(result, index / FPS))
        return {"fps": FPS, "rows": rows}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _read_pose(result, time: float) -> dict | None:
    if not result.pose_world_landmarks or not result.pose_landmarks:
        return None
    world = result.pose_world_landmarks[0]
    image = result.pose_landmarks[0]
    sample = {"t": time}
    for name, index in LANDMARKS.items():
        point = world[index]
        visibility = float(getattr(image[index], "visibility", 0.0) or 0.0)
        sample[name] = {
            "p": np.array([point.x, point.y, point.z], dtype=float),
            "v": visibility,
        }
    return sample


def _recover_motion(tracked: dict, external_sign: int) -> dict:
    rows = tracked["rows"]
    present = [row for row in rows if row is not None]
    if len(present) < FPS * 2:
        return _failed(
            "MediaPipe Pose Landmarker found a body on too few frames of the "
            "3D render. No joint angles were invented."
        )
    side = _working_side(present)
    good = _contiguous(rows, side)
    if len(good) < FPS * 2:
        return _failed(
            f"The {side} arm is the one the clip tracks, but the orbiting camera "
            "drops the pose too often to recover a continuous repetition. "
            "No joint angles were invented.",
            side,
        )
    flexed, fraction, counted = _flexion_fraction(good, side)
    if not flexed:
        return _failed(
            f"MediaPipe Pose Landmarker lite, on CPU, found the {side} arm on {counted} frames, "
            f"but the elbow is not a held bend: only {fraction:.0%} of those frames have an angle "
            "between 60 and 130 degrees, and the straighter frames are mixed in rather than a "
            "separate pose. The clip is an orbiting 3D render and the forearm often points at the "
            "camera, so the landmarker collapses the forearm toward a straight arm. Inverse "
            "kinematics was not run on those landmarks, and no joint angles were taken from the clip.",
            side,
        )
    cloud, scale = _to_opensim(good, side)
    if len(cloud) < FPS * 2:
        return _failed(
            "Shoulder and hip landmarks were not steady enough to build a body "
            "frame. No joint angles were invented.",
            side,
        )
    try:
        raj_table = _raj_ik(cloud, side)
        mobl_table = _mobl_ik(cloud, side)
    except Exception as exc:
        return _failed(f"OpenSim inverse kinematics failed: {exc}", side)
    arm_coord = f"arm_rot_{side[0]}"
    rotation = [row[arm_coord] for row in raj_table]
    span = max(rotation) - min(rotation)
    if span < 12.0:
        return _failed(
            f"Inverse kinematics ran, but {arm_coord} only moved {span:.1f} degrees. "
            "The landmarks did not recover the external-rotation sweep, so those "
            "angles were not used as the exercise.",
            side,
        )
    frames = _compose_frames(raj_table, mobl_table, side, external_sign)
    return {
        "kind": "volume",
        "fps": FPS,
        "title": "Shoulder external rotation with cable",
        "motion_recovered": True,
        "working_side": side,
        "method": (
            "MediaPipe Pose Landmarker lite on CPU, then OpenSim InverseKinematicsTool "
            "on Rajagopal2016. Shoulder muscle roles are MoBL-ARMS computeMomentArm "
            "values passed through the shared sign rule. The cable resists external "
            f"rotation, which is shoulder_rot sign {external_sign} on this model."
        ),
        "note": (
            "Not an exam item. The harness did not score this clip. "
            f"Tracked {side} arm, {len(frames)} frames, {arm_coord} span {span:.0f} deg. "
            "Rajagopal supplies the full-body bone meshes. Its arms have no muscles, "
            "so the tubes are the MoBL-ARMS shoulder paths posed by a second IK on the same landmarks."
        ),
        "rotation_span_deg": round(span, 2),
        "scale": round(scale, 4),
        "frames": frames,
    }


def _flexion_fraction(rows: list[dict], side: str) -> tuple[bool, float, int]:
    """Elbow angle in the body frame. The cable clip holds a bend near 90 degrees."""
    angles = []
    letter = side[0]
    for row in rows:
        frame, _torso = _body_frame(row)
        if frame is None:
            continue
        upper = frame[f"elbow_{letter}"] - frame[f"shoulder_{letter}"]
        forearm = frame[f"wrist_{letter}"] - frame[f"elbow_{letter}"]
        upper_length = float(np.linalg.norm(upper))
        forearm_length = float(np.linalg.norm(forearm))
        if upper_length < 1e-4 or forearm_length < 1e-4:
            continue
        cosine = float(np.clip(np.dot(upper, forearm) / (upper_length * forearm_length), -1.0, 1.0))
        angles.append(math.degrees(math.acos(cosine)))
    if len(angles) < int(FPS * 2):
        return False, 0.0, len(angles)
    fraction = sum(1 for angle in angles if 60.0 <= angle <= 130.0) / len(angles)
    low = float(np.percentile(angles, 10))
    return fraction >= 0.6 and low >= 45.0, fraction, len(angles)


def _working_side(rows: list[dict]) -> str:
    def mean_vis(names: tuple[str, str]) -> float:
        return float(np.mean([0.5 * (row[names[0]]["v"] + row[names[1]]["v"]) for row in rows]))

    left = mean_vis(("elbow_l", "wrist_l"))
    right = mean_vis(("elbow_r", "wrist_r"))
    return "left" if left >= right else "right"


def _contiguous(rows: list[dict | None], side: str) -> list[dict]:
    elbow, wrist = f"elbow_{side[0]}", f"wrist_{side[0]}"
    good_flags = []
    for row in rows:
        good_flags.append(row is not None and row[elbow]["v"] >= MIN_VISIBILITY and row[wrist]["v"] >= MIN_VISIBILITY)
    # Fill only short gaps so a missed detection does not invent a new pose.
    filled = good_flags[:]
    index = 0
    while index < len(filled):
        if filled[index]:
            index += 1
            continue
        end = index
        while end < len(filled) and not filled[end]:
            end += 1
        gap = (end - index) / FPS
        if 0 < index and end < len(filled) and gap <= HOLD_GAP_S:
            for cursor in range(index, end):
                filled[cursor] = True
        index = end
    runs: list[list[dict]] = []
    current: list[dict] = []
    last = None
    for row, keep in zip(rows, filled):
        if not keep or row is None:
            if current:
                runs.append(current)
                current = []
            last = None
            continue
        sample = row
        if last is not None and (row[elbow]["v"] < MIN_VISIBILITY or row[wrist]["v"] < MIN_VISIBILITY):
            sample = last
        current.append(sample)
        last = sample
    if current:
        runs.append(current)
    if not runs:
        return []
    return max(runs, key=len)


def _to_opensim(rows: list[dict], side: str) -> tuple[list[dict], float]:
    import opensim

    opensim.Logger.setLevelString("Off")
    model = opensim.Model(str(RAJ_PATH))
    state = model.initSystem()
    model.realizePosition(state)
    hip_r = _body_origin(model, state, "femur_r")
    hip_l = _body_origin(model, state, "femur_l")
    sho_r = _body_origin(model, state, "humerus_r")
    sho_l = _body_origin(model, state, "humerus_l")
    model_torso = float(np.linalg.norm((sho_r + sho_l) / 2 - (hip_r + hip_l) / 2))
    model_hip = (hip_r + hip_l) / 2
    lengths = []
    oriented = []
    for row in rows:
        frame, torso = _body_frame(row)
        if frame is None:
            continue
        lengths.append(torso)
        oriented.append((row["t"], frame))
    scale = model_torso / float(np.median(lengths))
    cloud = []
    for time, frame in oriented:
        points = {}
        for name in RAJ_MARKERS:
            points[name] = scale * frame[name] + model_hip
        cloud.append({"t": time, "points": points, "side": side})
    return cloud, scale


def _body_frame(row: dict) -> tuple[dict[str, np.ndarray] | None, float]:
    def ok(name: str) -> bool:
        return row[name]["v"] >= MIN_VISIBILITY or name.startswith("hip")

    if row["shoulder_l"]["v"] < MIN_VISIBILITY or row["shoulder_r"]["v"] < MIN_VISIBILITY:
        return None, 0.0
    if row["hip_l"]["v"] < 0.25 or row["hip_r"]["v"] < 0.25:
        return None, 0.0
    hip = 0.5 * (row["hip_l"]["p"] + row["hip_r"]["p"])
    shoulder = 0.5 * (row["shoulder_l"]["p"] + row["shoulder_r"]["p"])
    up = shoulder - hip
    torso = float(np.linalg.norm(up))
    if torso < 1e-4:
        return None, 0.0
    up = up / torso
    right = row["shoulder_r"]["p"] - row["shoulder_l"]["p"]
    right = right - up * np.dot(right, up)
    if np.linalg.norm(right) < 1e-4:
        return None, 0.0
    right = right / np.linalg.norm(right)
    forward = np.cross(up, right)
    forward = forward / np.linalg.norm(forward)
    # OpenSim: +X anterior, +Y up, +Z to the model's right.
    axes = np.column_stack((forward, up, right))
    local = {}
    for name in RAJ_MARKERS:
        local[name] = axes.T @ (row[name]["p"] - hip)
    return local, torso


def _raj_ik(cloud: list[dict], side: str) -> list[dict]:
    import opensim

    other = "r" if side == "left" else "l"
    model = opensim.Model(str(RAJ_PATH))
    for name, body_name in RAJ_MARKERS.items():
        if not _marker_kept(name, side):
            continue
        _add_marker(model, name, body_name)
    for name in LOCK_ALWAYS:
        _lock(model, name)
    for coord in (f"arm_flex_{other}", f"arm_add_{other}", f"arm_rot_{other}", f"elbow_flex_{other}"):
        _lock(model, coord)
    for coord in (
        "knee_angle_r",
        "knee_angle_l",
        "ankle_angle_r",
        "ankle_angle_l",
        "hip_flexion_r",
        "hip_flexion_l",
        "hip_adduction_r",
        "hip_adduction_l",
        "hip_rotation_r",
        "hip_rotation_l",
    ):
        _lock(model, coord)
    return _run_ik(model, cloud, [name for name in RAJ_MARKERS if _marker_kept(name, side)])


def _marker_kept(name: str, side: str) -> bool:
    # The untracked arm's elbow and wrist are mostly occluded. Both shoulders
    # stay, because they locate the torso. Knees and ankles are out of frame.
    other = "r" if side == "left" else "l"
    if name in (f"elbow_{other}", f"wrist_{other}"):
        return False
    return not name.startswith(("knee", "ankle"))


def _mobl_ik(cloud: list[dict], side: str) -> list[dict]:
    import opensim

    model = opensim.Model(str(MOBL_PATH))
    state = model.initSystem()
    model.realizePosition(state)
    shoulder_home = _body_origin(model, state, "humerus")
    _add_marker(model, "shoulder", "humerus")
    _add_marker(model, "elbow", "ulna")
    _add_marker(model, "wrist", "hand")
    free = {"elv_angle", "shoulder_elv", "shoulder_rot", "elbow_flexion"}
    coords = model.getCoordinateSet()
    for index in range(coords.getSize()):
        coord = coords.get(index)
        if coord.getName() not in free:
            coord.set_locked(True)
    # Re-init after locks. addMarker already needs a fresh system; _run_ik prints the file.
    mirrored = []
    for frame in cloud:
        points = frame["points"]
        shoulder = points[f"shoulder_{side[0]}"].copy()
        elbow = points[f"elbow_{side[0]}"].copy()
        wrist = points[f"wrist_{side[0]}"].copy()
        if side == "left":
            shoulder[2] *= -1
            elbow[2] *= -1
            wrist[2] *= -1
        shift = shoulder_home - shoulder
        mirrored.append(
            {
                "t": frame["t"],
                "points": {
                    "shoulder": shoulder + shift,
                    "elbow": elbow + shift,
                    "wrist": wrist + shift,
                },
            }
        )
    return _run_ik(model, mirrored, ["shoulder", "elbow", "wrist"])


def _compose_frames(raj_rows: list[dict], mobl_rows: list[dict], side: str, external_sign: int) -> list[dict]:
    import opensim

    opensim.Logger.setLevelString("Off")
    raj = opensim.Model(str(RAJ_PATH))
    raj_state = raj.initSystem()
    mobl = opensim.Model(str(MOBL_PATH))
    mobl_state = mobl.initSystem()
    required = required_signs(external_sign)
    mobl_by_time = {round(row["t"], 5): row for row in mobl_rows}
    frames = []
    for raj_row in raj_rows:
        _apply_row(raj, raj_state, raj_row)
        mobl_row = mobl_by_time.get(round(raj_row["t"], 5))
        muscles = {}
        if mobl_row is not None:
            _apply_row(mobl, mobl_state, mobl_row)
            muscles = _muscle_tubes(raj, raj_state, mobl, mobl_state, side, required)
        frames.append(
            {
                "t": round(raj_row["t"], 5),
                "bodies": _body_matrices(raj, raj_state),
                "muscles": muscles,
            }
        )
    return frames


# MoBL's ground frame is yawed relative to OpenSim: +X is the model's left,
# +Y is up, +Z is anterior. Anatomical offsets use +X anterior, +Y up, +Z right.
TORSO_PARENTS = {"thorax", "clavicle", "clavphant", "scapula", "scapphant"}


def _muscle_tubes(raj, raj_state, mobl, mobl_state, side: str, required: dict[str, int]) -> dict:
    return _tubes(raj, raj_state, mobl, mobl_state, side, _roles(mobl, mobl_state, required))


def _roles(mobl, state, required: dict[str, int]) -> dict[str, str]:
    arms = {}
    coords = mobl.getCoordinateSet()
    mobl.realizePosition(state)
    for name in SHOULDER_MUSCLES:
        muscle = mobl.getMuscles().get(name)
        arms[name] = {
            coord: float(muscle.computeMomentArm(state, coords.get(coord))) for coord in LOAD_COORDINATES
        }
    roles, _, _ = estimate(arms, required)
    return roles


def _tubes(raj, raj_state, mobl, mobl_state, side: str, roles: dict[str, str]) -> dict:
    tubes = {}
    for name in SHOULDER_MUSCLES:
        role = roles[name]
        if role == "inactive":
            continue
        path = _path_on_raj(raj, raj_state, mobl, mobl_state, name, side)
        if len(path) < 2:
            continue
        tubes[name] = {"role": role, "label": LABELS[name], "polyline": path, "radius": _radius(role)}
    return tubes


def _radius(role: str) -> float:
    if role == "prime_mover":
        return 0.014
    if role == "synergist":
        return 0.011
    return 0.008


def _path_on_raj(raj, raj_state, mobl, mobl_state, muscle_name: str, side: str) -> list[list[float]]:
    current = mobl.getMuscles().get(muscle_name).getGeometryPath().getCurrentPath(mobl_state)
    shift = _shoulder_shift(side)
    points = []
    for index in range(current.getSize()):
        point = current.get(index)
        parent_name = point.getParentFrame().getName()
        if parent_name not in PARENT_TO_RAJ:
            continue
        ground = point.getLocationInGround(mobl_state)
        placed = _place_on_raj(
            np.array([ground.get(0), ground.get(1), ground.get(2)], dtype=float),
            parent_name,
            side,
            raj,
            raj_state,
            mobl,
            mobl_state,
            shift,
        )
        points.append([round(float(v), 4) for v in placed])
    return points


def _place_on_raj(point_world, parent_name, side, raj, raj_state, mobl, mobl_state, shift) -> np.ndarray:
    anatomical = _anat_from_mobl(point_world)
    if parent_name in TORSO_PARENTS:
        thorax = _anat_from_mobl(_body_origin(mobl, mobl_state, "thorax"))
        relative = anatomical - thorax
        if side == "left":
            relative = relative.copy()
            relative[2] *= -1
        return _from_body(raj, raj_state, "torso", relative + shift)
    anchor_name = "humerus" if parent_name in ("humphant", "humphant1") else parent_name
    anchor = _anat_from_mobl(_body_origin(mobl, mobl_state, anchor_name))
    relative = anatomical - anchor
    if side == "left":
        relative = relative.copy()
        relative[2] *= -1
    raj_body = PARENT_TO_RAJ[parent_name]
    if raj_body in ("humerus", "ulna", "radius", "hand"):
        raj_body = f"{raj_body}_{side[0]}"
    # The offset is already in ground anatomical axes. Adding it in the body
    # frame would spin it again once the elbow is bent.
    return _body_origin(raj, raj_state, raj_body) + relative


def _anat_from_mobl(vector: np.ndarray) -> np.ndarray:
    return np.array([vector[2], vector[1], -vector[0]], dtype=float)


def _shoulder_shift(side: str) -> np.ndarray:
    shifts = _shoulder_shifts()
    return shifts[side]


_SHIFTS: dict[str, np.ndarray] | None = None


def _shoulder_shifts() -> dict[str, np.ndarray]:
    global _SHIFTS
    if _SHIFTS is not None:
        return _SHIFTS
    import opensim

    opensim.Logger.setLevelString("Off")
    raj = opensim.Model(str(RAJ_PATH))
    raj_state = raj.initSystem()
    raj.realizePosition(raj_state)
    mobl = opensim.Model(str(MOBL_PATH))
    mobl_state = mobl.initSystem()
    mobl.realizePosition(mobl_state)
    torso = _body_origin(raj, raj_state, "torso")
    relative_mobl = _anat_from_mobl(_body_origin(mobl, mobl_state, "humerus")) - _anat_from_mobl(
        _body_origin(mobl, mobl_state, "thorax")
    )
    shifts = {}
    for side, body_name in (("right", "humerus_r"), ("left", "humerus_l")):
        relative_raj = _body_origin(raj, raj_state, body_name) - torso
        mirrored = relative_mobl.copy()
        if side == "left":
            mirrored[2] *= -1
        shifts[side] = relative_raj - mirrored
    _SHIFTS = shifts
    return shifts


def _from_body(model, state, body_name: str, local: np.ndarray) -> np.ndarray:
    transform = model.getBodySet().get(body_name).getTransformInGround(state)
    rotation = np.array([[transform.R().get(r, c) for c in range(3)] for r in range(3)])
    origin = np.array([transform.p().get(i) for i in range(3)])
    return rotation @ local + origin


def _body_matrices(model, state) -> dict[str, list[float]]:
    model.realizePosition(state)
    matrices = {}
    bodies = model.getBodySet()
    for index in range(bodies.getSize()):
        body = bodies.get(index)
        transform = body.getTransformInGround(state)
        rotation = [[transform.R().get(r, c) for c in range(3)] for r in range(3)]
        origin = [transform.p().get(i) for i in range(3)]
        # Three.js Matrix4 is column-major.
        matrices[body.getName()] = [
            rotation[0][0], rotation[1][0], rotation[2][0], 0.0,
            rotation[0][1], rotation[1][1], rotation[2][1], 0.0,
            rotation[0][2], rotation[1][2], rotation[2][2], 0.0,
            origin[0], origin[1], origin[2], 1.0,
        ]
    return matrices


def _apply_row(model, state, row: dict) -> None:
    coords = model.getCoordinateSet()
    for name, value in row.items():
        if name == "t":
            continue
        coord = coords.get(name)
        if coord.getMotionType() == coord.Rotational:
            coord.setValue(state, math.radians(float(value)))
        else:
            coord.setValue(state, float(value))
    model.realizePosition(state)


def _run_ik(model, cloud: list[dict], marker_names: list[str]) -> list[dict]:
    import opensim

    opensim.Logger.setLevelString("Off")
    tmp = Path(tempfile.mkdtemp(prefix="ref-ik-"))
    try:
        model.finalizeConnections()
        model.initSystem()
        model_path = tmp / "model.osim"
        trc_path = tmp / "markers.trc"
        mot_path = tmp / "ik.mot"
        model.printToXML(str(model_path))
        _write_trc(trc_path, cloud, marker_names)
        tool = opensim.InverseKinematicsTool()
        tool.set_model_file(str(model_path))
        tool.set_marker_file(str(trc_path))
        tool.set_output_motion_file(str(mot_path))
        tool.setStartTime(float(cloud[0]["t"]))
        tool.setEndTime(float(cloud[-1]["t"]))
        tool.set_accuracy(1e-3)
        tool.run()
        return _read_mot(mot_path, [frame["t"] for frame in cloud])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _write_trc(path: Path, cloud: list[dict], marker_names: list[str]) -> None:
    rate = FPS
    lines = [
        f"PathFileType\t4\t(X/Y/Z)\t{path.name}",
        "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames",
        f"{rate}\t{rate}\t{len(cloud)}\t{len(marker_names)}\tm\t{rate}\t1\t{len(cloud)}",
        "Frame#\tTime\t" + "\t\t\t".join(marker_names) + "\t",
        "\t\t" + "\t".join(f"X{i}\tY{i}\tZ{i}" for i in range(1, len(marker_names) + 1)),
    ]
    for index, frame in enumerate(cloud, start=1):
        parts = [str(index), f"{frame['t']:.5f}"]
        for name in marker_names:
            point = frame["points"][name]
            parts.extend(f"{float(v):.6f}" for v in point)
        lines.append("\t".join(parts))
    path.write_text("\n".join(lines) + "\n")


def _read_mot(path: Path, times: list[float]) -> list[dict]:
    import opensim

    table = opensim.TimeSeriesTable(str(path))
    labels = [table.getColumnLabel(i) for i in range(table.getNumColumns())]
    rows = []
    count = table.getNumRows()
    for index in range(count):
        row = table.getRowAtIndex(index)
        values = {label: float(row[i]) for i, label in enumerate(labels)}
        time = times[index] if index < len(times) else index / FPS
        values["t"] = time
        rows.append(values)
    if len(rows) != len(times):
        # IK can drop the exact count; keep the solved samples and stamp times in order.
        for index, row in enumerate(rows):
            row["t"] = times[min(index, len(times) - 1)]
    return rows


def _add_marker(model, name: str, body_name: str) -> None:
    import opensim

    marker = opensim.Marker()
    marker.setName(name)
    marker.setParentFrameName(f"/bodyset/{body_name}")
    marker.set_location(opensim.Vec3(0, 0, 0))
    model.addMarker(marker)


def _lock(model, name: str) -> None:
    model.getCoordinateSet().get(name).set_locked(True)


def _body_origin(model, state, name: str) -> np.ndarray:
    point = model.getBodySet().get(name).getTransformInGround(state).p()
    return np.array([point.get(0), point.get(1), point.get(2)], dtype=float)


EXERCISE_FPS = 8
EXERCISE_STEPS = 24


def _exercise_motion() -> dict:
    """Pose the left arm in the cable exercise and sweep external rotation.

    The start pose is the moment-arm posture: upper arm at the side, elbow at
    90 degrees. The sweep uses the arm_rot_l range endpoint that carries the
    hand away from the midline. Nothing here is read from the reference video.
    """
    import opensim

    opensim.Logger.setLevelString("Off")
    raj = opensim.Model(str(RAJ_PATH))
    raj_state = raj.initSystem()
    _pose_raj_start(raj, raj_state)
    sweep = _external_sweep_degrees(raj, raj_state)
    mobl = opensim.Model(str(MOBL_PATH))
    mobl_state = mobl.initSystem()
    _pose_mobl_measurement(mobl, mobl_state)
    roles = _roles(mobl, mobl_state, required_signs(external_rotation_sign(MOBL_PATH)))
    baked = _bake_muscles(raj, raj_state, mobl, mobl_state, "left", roles)
    frames = []
    for index in range(EXERCISE_STEPS + 1):
        amount = math.sin(math.pi * index / EXERCISE_STEPS)
        _set_deg(raj, raj_state, "arm_rot_l", sweep * amount)
        _set_deg(raj, raj_state, "elbow_flex_l", 90.0)
        frames.append(
            {
                "t": round(index / EXERCISE_FPS, 5),
                "bodies": _body_matrices(raj, raj_state),
                "muscles": _tubes_from_bake(raj, raj_state, baked),
            }
        )
    return {
        "kind": "volume",
        "fps": EXERCISE_FPS,
        "title": "Shoulder external rotation with cable",
        "motion_recovered": False,
        "playable": True,
        "working_side": "left",
        "sweep_deg": round(sweep, 2),
        "method": (
            "Left arm posed on Rajagopal2016 in the cable exercise: upper arm at the side, "
            "elbow at 90 degrees, the posture used to read moment arms. "
            f"arm_rot_l then sweeps {abs(sweep):.0f} degrees so the forearm moves out from "
            "the midline and returns. That direction is the model's arm_rot_l range, "
            "not an angle read from the video."
        ),
        "note": (
            "Not an exam item. The harness did not score this clip. "
            "Shoulder colors are MoBL-ARMS computeMomentArm roles for a cable that resists "
            "external rotation. No pose landmarks were read from the reference video."
        ),
        "frames": frames,
    }


def _pose_raj_start(model, state) -> None:
    _set_deg(model, state, "arm_flex_l", 0.0)
    _set_deg(model, state, "arm_add_l", 0.0)
    _set_deg(model, state, "arm_rot_l", 0.0)
    _set_deg(model, state, "elbow_flex_l", 90.0)


def _pose_mobl_measurement(model, state) -> None:
    for name, degrees in (
        ("elbow_flexion", 90.0),
        ("elv_angle", 0.0),
        ("shoulder_elv", 0.0),
        ("shoulder_rot", 0.0),
    ):
        _set_deg(model, state, name, degrees)


def _set_deg(model, state, name: str, degrees: float) -> None:
    coord = model.getCoordinateSet().get(name)
    radians = min(max(math.radians(degrees), coord.getRangeMin()), coord.getRangeMax())
    coord.setValue(state, radians)
    model.realizePosition(state)


def _external_sweep_degrees(model, state) -> float:
    """Return the arm_rot_l endpoint that moves the left hand away from midline."""
    coord = model.getCoordinateSet().get("arm_rot_l")
    start = _hand_z(model, state)
    best = 0.0
    best_z = start
    for endpoint in (math.degrees(coord.getRangeMin()), math.degrees(coord.getRangeMax())):
        _set_deg(model, state, "arm_rot_l", endpoint)
        _set_deg(model, state, "elbow_flex_l", 90.0)
        z_value = _hand_z(model, state)
        if z_value < best_z:
            best_z = z_value
            best = endpoint
    _pose_raj_start(model, state)
    if abs(best) < 1.0 or start - best_z < 0.05:
        raise RuntimeError("arm_rot_l did not move the left hand away from the midline")
    return best


def _hand_z(model, state) -> float:
    return float(_body_origin(model, state, "hand_l")[2])


def _bake_muscles(raj, raj_state, mobl, mobl_state, side: str, roles: dict[str, str]) -> dict:
    shift = _shoulder_shift(side)
    baked = {}
    for name in SHOULDER_MUSCLES:
        role = roles[name]
        if role == "inactive":
            continue
        current = mobl.getMuscles().get(name).getGeometryPath().getCurrentPath(mobl_state)
        stations = []
        for index in range(current.getSize()):
            point = current.get(index)
            parent_name = point.getParentFrame().getName()
            if parent_name not in PARENT_TO_RAJ:
                continue
            ground = point.getLocationInGround(mobl_state)
            world = _place_on_raj(
                np.array([ground.get(0), ground.get(1), ground.get(2)], dtype=float),
                parent_name,
                side,
                raj,
                raj_state,
                mobl,
                mobl_state,
                shift,
            )
            body_name = _raj_body_name(parent_name, side)
            rotation, origin = _body_pose(raj, raj_state, body_name)
            stations.append((body_name, rotation.T @ (world - origin)))
        if len(stations) >= 2:
            baked[name] = {"role": role, "label": LABELS[name], "stations": stations}
    return baked


def _raj_body_name(parent_name: str, side: str) -> str:
    body_name = PARENT_TO_RAJ[parent_name]
    if body_name in ("humerus", "ulna", "radius", "hand"):
        return f"{body_name}_{side[0]}"
    return body_name


def _tubes_from_bake(model, state, baked: dict) -> dict:
    tubes = {}
    for name, spec in baked.items():
        polyline = []
        for body_name, local in spec["stations"]:
            rotation, origin = _body_pose(model, state, body_name)
            world = rotation @ local + origin
            polyline.append([round(float(value), 4) for value in world])
        tubes[name] = {"role": spec["role"], "label": spec["label"], "polyline": polyline}
    return tubes


def _body_pose(model, state, name: str) -> tuple[np.ndarray, np.ndarray]:
    transform = model.getBodySet().get(name).getTransformInGround(state)
    rotation = np.array([[transform.R().get(row, col) for col in range(3)] for row in range(3)])
    origin = np.array([transform.p().get(index) for index in range(3)], dtype=float)
    return rotation, origin


def _failed(reason: str, side: str = "left") -> dict:
    return {
        "kind": "volume",
        "fps": 1,
        "title": "Shoulder external rotation with cable",
        "motion_recovered": False,
        "working_side": side,
        "method": (
            "Rajagopal2016 bone meshes, shown in the model's default pose. "
            "Shoulder tubes are MoBL-ARMS paths placed on those bones. Their colors are "
            "computeMomentArm roles for a cable that resists external rotation, read with "
            "the elbow at 90 degrees and the upper arm at the side. That posture is only "
            "the moment-arm measurement. It is not a pose taken from the clip."
        ),
        "blocker": reason,
        "note": (
            "Not an exam item. The harness did not score this clip. "
            f"The tubes are on the {side} shoulder, which is the arm in the reference clip."
        ),
        "frames": [_default_frame(side)],
    }


def _default_frame(side: str = "left") -> dict:
    import opensim

    opensim.Logger.setLevelString("Off")
    raj = opensim.Model(str(RAJ_PATH))
    raj_state = raj.initSystem()
    raj.realizePosition(raj_state)
    mobl = opensim.Model(str(MOBL_PATH))
    mobl_state = mobl.initSystem()
    mobl.realizePosition(mobl_state)
    required = required_signs(external_rotation_sign(MOBL_PATH))
    coords = mobl.getCoordinateSet()
    saved = [(name, coords.get(name).getValue(mobl_state)) for name in LOAD_COORDINATES]
    for name, degrees in (
        ("elbow_flexion", 90.0),
        ("elv_angle", 0.0),
        ("shoulder_elv", 0.0),
        ("shoulder_rot", 0.0),
    ):
        coord = coords.get(name)
        radians = min(max(math.radians(degrees), coord.getRangeMin()), coord.getRangeMax())
        coord.setValue(mobl_state, radians)
    mobl.realizePosition(mobl_state)
    roles = _roles(mobl, mobl_state, required)
    for name, value in saved:
        coords.get(name).setValue(mobl_state, value)
    mobl.realizePosition(mobl_state)
    return {
        "t": 0.0,
        "bodies": _body_matrices(raj, raj_state),
        "muscles": _tubes(raj, raj_state, mobl, mobl_state, side, roles),
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
