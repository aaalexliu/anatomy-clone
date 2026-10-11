"""Roles from the sign of the finite-difference moment arm.

A muscle's contribution on a clip is the sum of (moment arm × required moment
sign) over coordinates the load actually asks for. Large positive contributions
are prime movers, smaller ones are synergists, and the opposite sign is the
antagonist. A stabilizer is a different muscle that opposes the moment those
movers would spill onto a joint the clip holds still.
"""

from __future__ import annotations

PRIME = 0.60
SYNERGIST = 0.25
HELD_ARM = 0.01


def estimate(arms: dict[str, dict[str, float]], required: dict[str, int]) -> tuple[dict[str, str], dict[str, float], float]:
    contribution = {
        muscle: sum(row[coord] * required[coord] for coord, sign in required.items() if sign != 0)
        for muscle, row in arms.items()
    }
    positive = [value for value in contribution.values() if value > 0.0]
    peak = max(positive) if positive else 0.0
    roles = {}
    scores = {}
    for muscle, value in contribution.items():
        if peak > 0.0 and value >= PRIME * peak:
            roles[muscle] = "prime_mover"
            scores[muscle] = value
        elif peak > 0.0 and value >= SYNERGIST * peak:
            roles[muscle] = "synergist"
            scores[muscle] = value
        elif peak > 0.0 and value <= -SYNERGIST * peak:
            roles[muscle] = "antagonist"
            scores[muscle] = abs(value)
        else:
            roles[muscle] = "inactive"
            scores[muscle] = abs(value)

    agonists = [muscle for muscle, role in roles.items() if role in ("prime_mover", "synergist")]
    for coord, sign in required.items():
        if sign != 0:
            continue
        spill = sum(arms[muscle][coord] for muscle in agonists)
        if abs(spill) < HELD_ARM:
            continue
        for muscle, row in arms.items():
            if roles[muscle] != "inactive":
                continue
            if spill * row[coord] < 0.0 and abs(row[coord]) >= HELD_ARM:
                roles[muscle] = "stabilizer"
                scores[muscle] = abs(row[coord])
    return roles, scores, 0.52
