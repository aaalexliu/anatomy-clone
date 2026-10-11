"""Numpy toy rig: stick skeleton and muscle polylines.

Attachments are approximate textbook origins, insertions, and via points for a
right-side figure. They are not copied from any commercial anatomy product.
+X anterior, +Y superior, +Z to the model's right. Lengths are meters.
Angles are degrees. Moment arms are meters per radian, OpenSim sign:
r = -dL/dq, so a positive moment arm produces a positive coordinate moment.
"""

from __future__ import annotations

import numpy as np

COORDINATES = (
    "hip_flexion",
    "knee_flexion",
    "shoulder_flexion",
    "shoulder_abduction",
    "shoulder_horizontal_abduction",
    "shoulder_external_rotation",
    "elbow_flexion",
    "scapular_retraction",
)

JOINTS = (
    "pelvis",
    "hip",
    "knee",
    "ankle",
    "shoulder",
    "elbow",
    "wrist",
)

BONES = (
    ("pelvis", "hip"),
    ("hip", "knee"),
    ("knee", "ankle"),
    ("pelvis", "shoulder"),
    ("shoulder", "elbow"),
    ("elbow", "wrist"),
)

THIGH = 0.42
SHANK = 0.40
HUMERUS = 0.30
FOREARM = 0.26

# (segment, local xyz). Patella is the knee-angle bisector, so the vastus
# via stays anterior to the knee instead of collapsing in deep flexion.
MUSCLES = (
    {
        "name": "biceps_brachii",
        "points": (
            ("trunk", (0.030, 0.555, 0.170)),
            ("forearm", (0.028, -0.050, 0.008)),
        ),
    },
    {
        "name": "brachialis",
        "points": (
            ("humerus", (0.016, -0.160, 0.000)),
            ("forearm", (0.018, -0.035, 0.000)),
        ),
    },
    {
        "name": "brachioradialis",
        "points": (
            ("humerus", (0.006, -0.255, 0.018)),
            ("forearm", (0.014, -0.230, 0.016)),
        ),
    },
    {
        "name": "triceps_brachii",
        "points": (
            ("trunk", (-0.020, 0.485, 0.170)),
            ("forearm", (-0.048, 0.000, 0.000)),
            ("forearm", (-0.020, -0.042, 0.000)),
        ),
    },
    {
        "name": "anterior_deltoid",
        "points": (
            ("trunk", (0.055, 0.575, 0.160)),
            ("humerus", (0.018, -0.145, 0.012)),
        ),
    },
    {
        "name": "posterior_deltoid",
        "points": (
            ("trunk", (-0.060, 0.555, 0.155)),
            ("humerus", (-0.016, -0.145, 0.016)),
        ),
    },
    {
        "name": "gluteus_maximus",
        "points": (
            ("trunk", (-0.090, 0.040, 0.110)),
            ("trunk", (-0.100, -0.100, 0.160)),
            ("femur", (-0.055, -0.070, 0.010)),
        ),
    },
    {
        "name": "biceps_femoris",
        "points": (
            ("trunk", (-0.050, -0.115, 0.140)),
            ("shank", (-0.028, -0.055, 0.015)),
        ),
    },
    {
        "name": "vastus_lateralis",
        "points": (
            ("femur", (0.028, -0.150, 0.025)),
            ("patella", (0.048, 0.000, 0.012)),
            ("shank", (0.030, -0.060, 0.008)),
        ),
    },
    {
        "name": "iliopsoas",
        "points": (
            ("trunk", (0.065, 0.060, 0.110)),
            ("femur", (0.028, -0.040, 0.000)),
        ),
    },
    {
        "name": "infraspinatus",
        "points": (
            ("scapula", (-0.028, -0.005, 0.012)),
            ("humerus", (-0.024, -0.028, 0.020)),
        ),
    },
    {
        "name": "teres_minor",
        "points": (
            ("scapula", (-0.022, -0.055, 0.004)),
            ("humerus", (-0.020, -0.048, 0.016)),
        ),
    },
    {
        "name": "subscapularis",
        "points": (
            ("scapula", (0.028, -0.015, 0.006)),
            ("humerus", (0.024, -0.030, -0.006)),
        ),
    },
    {
        "name": "supraspinatus",
        "points": (
            ("scapula", (0.000, 0.060, 0.000)),
            ("humerus", (0.000, -0.010, 0.036)),
        ),
    },
    {
        "name": "middle_trapezius",
        "points": (
            ("trunk", (-0.070, 0.440, 0.000)),
            ("scapula", (0.000, 0.020, 0.045)),
        ),
    },
    {
        "name": "lower_trapezius",
        "points": (
            ("trunk", (-0.060, 0.220, 0.000)),
            ("scapula", (-0.008, 0.030, 0.030)),
        ),
    },
    {
        "name": "rhomboid_major",
        "points": (
            ("trunk", (-0.065, 0.380, 0.000)),
            ("scapula", (0.000, -0.020, -0.015)),
        ),
    },
    {
        "name": "latissimus_dorsi",
        "points": (
            ("trunk", (-0.050, 0.180, 0.070)),
            ("humerus", (0.020, -0.040, 0.010)),
        ),
    },
    {
        "name": "pectoralis_major",
        "points": (
            ("trunk", (0.075, 0.400, 0.080)),
            ("humerus", (0.016, -0.042, 0.018)),
        ),
    },
)


def _rot_x(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _rot_y(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def _rot_z(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _q(angles: dict[str, float]) -> dict[str, float]:
    return {name: float(angles.get(name, 0.0)) for name in COORDINATES}


def frames(angles: dict[str, float]) -> dict[str, np.ndarray]:
    """Segment origin and rotation (maps local coordinates into the world)."""
    q = _q(angles)
    pelvis = np.array([0.0, 0.95, 0.0])
    hip = pelvis + np.array([0.0, -0.08, 0.15])
    shoulder = pelvis + np.array([0.0, 0.52, 0.18])
    r_femur = _rot_z(q["hip_flexion"])
    r_shank = _rot_z(q["hip_flexion"] - q["knee_flexion"])
    r_patella = _rot_z(q["hip_flexion"] - 0.5 * q["knee_flexion"])
    # Abduction lifts the right arm toward +Z. Horizontal abduction then
    # swings it posteriorly. External rotation spins the humerus so the
    # anterior surface turns laterally. Zero extra angles match the sagittal rig.
    r_hum = (
        _rot_y(-q["shoulder_horizontal_abduction"])
        @ _rot_z(q["shoulder_flexion"])
        @ _rot_x(-q["shoulder_abduction"])
        @ _rot_y(-q["shoulder_external_rotation"])
    )
    r_fore = r_hum @ _rot_z(q["elbow_flexion"])
    knee = hip + r_femur @ np.array([0.0, -THIGH, 0.0])
    elbow = shoulder + r_hum @ np.array([0.0, -HUMERUS, 0.0])
    retract = q["scapular_retraction"]
    scapula = pelvis + np.array([-0.02, 0.48, 0.14]) + np.array([-0.0010 * retract, 0.0, -0.0008 * retract])
    return {
        "trunk": (pelvis, np.eye(3)),
        "femur": (hip, r_femur),
        "shank": (knee, r_shank),
        "patella": (knee, r_patella),
        "humerus": (shoulder, r_hum),
        "forearm": (elbow, r_fore),
        "scapula": (scapula, np.eye(3)),
    }


def joint_positions(angles: dict[str, float]) -> dict[str, np.ndarray]:
    seg = frames(angles)
    pelvis, _ = seg["trunk"]
    hip, r_femur = seg["femur"]
    knee, r_shank = seg["shank"]
    shoulder, r_hum = seg["humerus"]
    elbow, r_fore = seg["forearm"]
    return {
        "pelvis": pelvis,
        "hip": hip,
        "knee": knee,
        "ankle": knee + r_shank @ np.array([0.0, -SHANK, 0.0]),
        "shoulder": shoulder,
        "elbow": elbow,
        "wrist": elbow + r_fore @ np.array([0.0, -FOREARM, 0.0]),
    }


def _world_point(seg: dict, spec: tuple) -> np.ndarray:
    name, local = spec
    origin, rotation = seg[name]
    return origin + rotation @ np.asarray(local, dtype=float)


def muscle_polylines(angles: dict[str, float]) -> dict[str, np.ndarray]:
    seg = frames(angles)
    out = {}
    for muscle in MUSCLES:
        pts = np.vstack([_world_point(seg, spec) for spec in muscle["points"]])
        out[muscle["name"]] = pts
    return out


def _length(points: np.ndarray) -> float:
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def moment_arms(angles: dict[str, float], eps_deg: float = 0.05) -> dict[str, dict[str, float]]:
    """Central finite difference of polyline length. q is converted to radians."""
    base = _q(angles)
    names = [muscle["name"] for muscle in MUSCLES]
    out = {name: {} for name in names}
    eps_rad = float(np.deg2rad(eps_deg))
    for coord in COORDINATES:
        plus = dict(base)
        minus = dict(base)
        plus[coord] = base[coord] + eps_deg
        minus[coord] = base[coord] - eps_deg
        lp = muscle_polylines(plus)
        lm = muscle_polylines(minus)
        for name in names:
            dlen = _length(lp[name]) - _length(lm[name])
            out[name][coord] = -dlen / (2.0 * eps_rad)
    return out
