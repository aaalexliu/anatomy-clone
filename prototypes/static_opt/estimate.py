"""Roles from a minimum-activation static optimization.

Approximate physiological cross-sections set Fmax. Activations minimize the
sum of squares while matching the required joint moments, including zeros on
joints the clip holds still. There is no co-contraction term, so an antagonist
stays quiet unless the moment balance needs it. That is a different rule from
listing every muscle whose moment-arm sign agrees.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

# Approximate textbook PCSA (cm^2) times 30 N/cm^2. Order of magnitude only.
FMAX = {
    "biceps_brachii": 150.0,
    "brachialis": 210.0,
    "brachioradialis": 45.0,
    "triceps_brachii": 450.0,
    "anterior_deltoid": 240.0,
    "posterior_deltoid": 180.0,
    "gluteus_maximus": 900.0,
    "biceps_femoris": 300.0,
    "vastus_lateralis": 750.0,
    "iliopsoas": 360.0,
    "infraspinatus": 240.0,
    "teres_minor": 90.0,
    "subscapularis": 420.0,
    "supraspinatus": 150.0,
    "middle_trapezius": 240.0,
    "lower_trapezius": 240.0,
    "rhomboid_major": 180.0,
    "latissimus_dorsi": 450.0,
    "pectoralis_major": 450.0,
}

TARGET_NM = 4.0
PRIME = 0.70
FLOOR = 0.25
ABS_FLOOR = 0.05
# Held joints the toy can actually balance. Other coordinates are constrained
# only when the load names them; a hard zero on every unused axis makes the
# small muscle set infeasible.
HELD = ("hip_flexion", "knee_flexion", "shoulder_flexion", "elbow_flexion")


def _solve(matrix: np.ndarray, moment: np.ndarray) -> tuple[np.ndarray, float]:
    width = matrix.shape[1]
    start = np.clip(np.linalg.lstsq(matrix, moment, rcond=None)[0], 0.0, 1.0)
    result = minimize(
        lambda activation: float(activation @ activation),
        start,
        jac=lambda activation: 2.0 * activation,
        bounds=[(0.0, 1.0)] * width,
        constraints={
            "type": "eq",
            "fun": lambda activation: matrix @ activation - moment,
            "jac": lambda activation: matrix,
        },
        method="SLSQP",
        options={"maxiter": 400, "ftol": 1e-14},
    )
    activation = np.clip(result.x, 0.0, 1.0)
    scale = float(np.linalg.norm(moment)) + 1e-9
    residual = float(np.linalg.norm(matrix @ activation - moment)) / scale
    return activation, residual


def _constrained(required: dict[str, int]) -> list[str]:
    return [coord for coord, sign in required.items() if sign != 0 or coord in HELD]


def estimate(arms: dict[str, dict[str, float]], required: dict[str, int]) -> tuple[dict[str, str], dict[str, float], float]:
    muscles = list(arms)
    coords = _constrained(required)
    matrix = np.zeros((len(coords), len(muscles)))
    for index, muscle in enumerate(muscles):
        for row, coord in enumerate(coords):
            matrix[row, index] = arms[muscle][coord] * FMAX[muscle]
    moment = np.array([required[coord] * TARGET_NM for coord in coords], dtype=float)
    activation = np.zeros(len(muscles))
    residual = 1.0
    for _ in range(6):
        activation, residual = _solve(matrix, moment)
        if residual < 0.08:
            break
        moment *= 0.5

    peak = float(activation.max()) if len(activation) else 0.0
    roles = {}
    scores = {}
    for muscle, value in zip(muscles, activation):
        value = float(value)
        scores[muscle] = value
        helpful = sum(arms[muscle][coord] * required[coord] for coord, sign in required.items() if sign != 0)
        counted = value >= ABS_FLOOR and peak > 0.0 and value >= FLOOR * peak
        if not counted:
            roles[muscle] = "inactive"
        elif helpful > 0.004 and value >= PRIME * peak:
            roles[muscle] = "prime_mover"
        elif helpful > 0.004:
            roles[muscle] = "synergist"
        elif helpful < -0.004:
            roles[muscle] = "antagonist"
        else:
            roles[muscle] = "stabilizer"
    confidence = 0.66 if residual < 0.08 else 0.34
    return roles, scores, confidence
