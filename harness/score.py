"""Score frozen exam items from emission.json.

The driving track and the held-out track must differ. A missing held-out track
abstains joint path. Playback is render-only and is never opened.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKING = ("prime_mover", "synergist", "stabilizer")
RANK = {"prime_mover": 0, "synergist": 1, "stabilizer": 2}


def score_runs(runs: Path, exam: Path) -> None:
    vocab = _read(exam / "vocab.json")
    spec = _read(exam / "score_spec.json")
    gates = _read(exam / "gates.json")
    action = _read(exam / "action_table.json")
    by_id = {item["id"]: item for item in spec["items"]}
    limits = {}
    for path in (exam / "limits").glob("*.json"):
        payload = _read(path)
        limits[payload["skeleton"]] = payload
    labels = {path.stem: _read(path) for path in (exam / "labels").glob("*.json")}
    for emission_path in sorted(runs.glob("*/*/emission.json")):
        try:
            emission = _read(emission_path)
        except json.JSONDecodeError as exc:
            _write(emission_path.parent / "score.json", _invalid("unknown", emission_path.parent.name, f"Emission is not JSON: {exc}"))
            continue
        prototype_id = emission.get("prototype_id") or emission_path.parents[1].name
        item_id = emission.get("item_id") or emission_path.parent.name
        problems = validate_emission(emission, vocab)
        if problems:
            _write(emission_path.parent / "score.json", _invalid(prototype_id, item_id, "; ".join(problems)))
            continue
        item = by_id.get(item_id)
        if item is None:
            _write(emission_path.parent / "score.json", _invalid(prototype_id, item_id, "No frozen exam item for this id."))
            continue
        label = labels.get(item["label_set"])
        if label is None:
            _write(emission_path.parent / "score.json", _invalid(prototype_id, item_id, "Frozen label set is missing."))
            continue
        heldout = None
        heldout_path = exam / "heldout" / f"{item_id}.json"
        if heldout_path.exists():
            heldout = _read(heldout_path)
        payload = score_emission(
            emission,
            spec=item,
            labels=label,
            action=action,
            limits=limits,
            gates=gates,
            heldout=heldout,
        )
        _write(emission_path.parent / "score.json", payload)


def score_emission(emission, *, spec, labels, action, limits, gates, heldout) -> dict:
    legality = score_legality(emission, limits)
    joint_path = score_joint_path(emission, heldout, gates)
    muscle_role = score_muscle_role(emission, spec, labels, action, gates)
    negative = score_negative(spec, muscle_role)
    couple = score_force_couple(emission, spec, action)
    parts = {
        "legality": legality,
        "joint_path": joint_path,
        "muscle_role": muscle_role,
        "negative_control": negative,
        "force_couple": couple,
    }
    return {
        "prototype_id": emission["prototype_id"],
        "item_id": emission["item_id"],
        "overall": rollup(spec, parts),
        **parts,
    }


def rollup(spec: dict, parts: dict) -> dict:
    if spec.get("negative_control"):
        for key in ("legality", "joint_path"):
            if parts[key]["status"] in ("fail", "invalid"):
                return {"status": parts[key]["status"], "reason": parts[key]["reason"]}
        return {
            "status": parts["negative_control"]["status"],
            "reason": parts["negative_control"]["reason"],
        }
    for key in ("legality", "joint_path", "muscle_role", "force_couple"):
        if parts[key]["status"] in ("fail", "invalid"):
            return {"status": parts[key]["status"], "reason": parts[key]["reason"]}
    muscle = parts["muscle_role"]
    if muscle["status"] == "pass":
        reason = muscle["reason"]
        if parts["joint_path"]["status"] == "abstain":
            reason = f"{reason} {parts['joint_path']['reason']}"
        return {"status": "pass", "reason": reason}
    return {"status": muscle["status"], "reason": muscle["reason"]}


def score_legality(emission: dict, limits: dict) -> dict:
    skeleton = emission["provenance"]["skeleton"]
    table = limits.get(skeleton)
    if table is None:
        return _status("abstain", f"No limits registered for skeleton {skeleton}.")
    bounds = table["coordinates"]
    coords = emission["joint_angles"]["coordinates"]
    missing = [name for name in coords if name not in bounds]
    outside = []
    for frame, row in enumerate(emission["joint_angles"]["values"]):
        for name, value in zip(coords, row):
            if name not in bounds:
                continue
            lo = bounds[name]["min"]
            hi = bounds[name]["max"]
            if value < lo or value > hi:
                outside.append(f"{name} {value:.1f}° at frame {frame} (limit {lo}° to {hi}°)")
                if len(outside) >= 3:
                    break
        if len(outside) >= 3:
            break
    if outside:
        return _status("fail", "Outside a hard limit: " + "; ".join(outside) + ".")
    if missing:
        return _status("abstain", "No limit for " + ", ".join(missing) + ".")
    return _status("pass", f"Every frame is inside {skeleton} limits.")


def score_joint_path(emission: dict, heldout, gates: dict) -> dict:
    if heldout is None:
        return _status("abstain", "No held-out track.")
    drive = emission["provenance"]["drive_track_id"]
    held_id = heldout.get("track_id")
    if drive is not None and held_id is not None and drive == held_id:
        return _status(
            "invalid",
            "Drive track id matches the held-out track id. The result is invalid.",
        )
    if heldout.get("mirror") or heldout.get("cropped"):
        return _status("abstain", "Held-out clip is a mirror or cropped.")
    if heldout.get("unit") != "deg" or emission["joint_angles"]["unit"] != "deg":
        return _status("invalid", "Joint path comparison requires degrees.")
    rule = gates["joint_path"]
    majors = rule["major_coordinates"]
    visible = [name for name in majors if _joint_visible(name, emission, heldout)]
    fraction = len(visible) / len(majors) if majors else 0.0
    if fraction < rule["min_visible_fraction"]:
        return _status("abstain", f"Only {fraction:.0%} of major joints are visible.")
    means = []
    worst = 0.0
    for name in visible:
        errors = _errors(name, emission["joint_angles"], heldout)
        if len(errors) < 2:
            return _status("abstain", "Held-out track does not cover the emission.")
        means.append(sum(errors) / len(errors))
        worst = max(worst, max(errors))
    mean = sum(means) / len(means)
    if mean < rule["mean_abs_deg_max"] and worst <= rule["max_abs_deg_max"]:
        return _status("pass", f"Mean error {mean:.1f}°, max {worst:.1f}°.")
    return _status("fail", f"Mean error {mean:.1f}°, max {worst:.1f}°.")


def score_muscle_role(emission, spec, labels, action, gates) -> dict:
    if not emission["load"]["direction_known"]:
        return _status("abstain", "Load direction is unknown.")
    block = emission["muscle_roles"]
    index = len(block["times_s"]) // 2
    names = block["names"]
    roles = dict(zip(names, block["roles"][index]))
    scores = dict(zip(names, block["scores"][index]))
    ranked = []
    for name, role in roles.items():
        if role in RANK:
            ranked.append((RANK[role], -float(scores.get(name, 0.0)), name))
    ranked.sort()
    predicted = [name for _, _, name in ranked[:5]]
    reference = _unique(labels["prime_movers"] + labels["synergists"] + labels["stabilizers"])
    denom = min(5, len(reference))
    overlap = 1.0 if denom == 0 and not predicted else (len(set(predicted) & set(reference)) / denom if denom else 0.0)
    primes = [name for name, role in roles.items() if role == "prime_mover"]
    violations = _sign_violations(primes, action, spec["task_moments"])
    minimum = gates["muscle_role"]["top5_overlap_min"]
    detail = {
        "overlap": round(overlap, 4),
        "predicted_top5": predicted,
        "reference_working": reference,
        "sign_violations": violations,
    }
    if violations:
        return _status(
            "fail",
            "Prime mover with the wrong moment-arm sign: " + "; ".join(violations) + ".",
            **detail,
        )
    if overlap + 1e-9 < minimum:
        return _status(
            "fail",
            f"Top-5 overlap {overlap:.2f} is below {minimum:.2f}. Predicted {', '.join(predicted) or 'none'}; reference {', '.join(reference) or 'none'}.",
            **detail,
        )
    return _status(
        "pass",
        f"Top-5 overlap {overlap:.2f}. Prime movers match the action-table sign.",
        **detail,
    )


def score_negative(spec: dict, muscle_role: dict) -> dict:
    if not spec.get("negative_control"):
        return _status("not_applicable", "This item is not a negative control.")
    status = muscle_role["status"]
    if status == "fail":
        return _status("pass", "Muscle role failed, as required for a negative control.")
    if status == "pass":
        return _status("fail", "Muscle role passed. The negative control did not fail.")
    if status == "abstain":
        return _status("abstain", "Muscle role abstained, so the negative control abstains.")
    return _status("invalid", "Muscle role is invalid, so the negative control is invalid.")


def score_force_couple(emission, spec, action) -> dict:
    claim = spec.get("force_couple")
    if not claim:
        return _status("not_applicable", "This item has no force-couple claim.")
    block = emission["muscle_roles"]
    index = len(block["times_s"]) // 2
    roles = dict(zip(block["names"], block["roles"][index]))
    groups = claim["groups"]
    sides = [_couple_side(group, roles) for group in groups]
    coordinate = claim["coordinate"]
    signs = []
    for group in groups:
        muscle = group[0]
        signs.append(int(action["muscles"].get(muscle, {}).get(coordinate, 0)))
    table_opposes = signs[0] * signs[1] < 0
    if "absent" in sides:
        return _status("fail", "One side of the force couple is missing from the roles.")
    if sides[0] == sides[1]:
        return _status("fail", "Both sides of the force couple have the same job.")
    if not table_opposes:
        return _status("fail", "Frozen action table does not give the two groups opposite signs.")
    return _status(
        "pass",
        f"{', '.join(groups[0])} ({sides[0]}) opposes {', '.join(groups[1])} ({sides[1]}).",
    )


def validate_emission(emission: dict, vocab: dict) -> list[str]:
    problems = []
    for key in ("prototype_id", "item_id", "joint_angles", "muscle_roles", "load", "confidence", "provenance"):
        if key not in emission:
            problems.append(f"missing {key}")
    if problems:
        return problems
    angles = emission["joint_angles"]
    roles = emission["muscle_roles"]
    provenance = emission["provenance"]
    for key in ("skeleton", "tracker", "estimator", "motion_source", "drive_track_id"):
        if key not in provenance:
            problems.append(f"provenance missing {key}")
    if angles.get("unit") != "deg":
        problems.append("joint angles must be degrees")
    times = angles.get("times_s") or []
    coords = angles.get("coordinates") or []
    values = angles.get("values") or []
    if len(values) != len(times) or len(times) < 2:
        problems.append("joint angle rows do not match times")
    if any(len(row) != len(coords) for row in values):
        problems.append("joint angle width does not match coordinates")
    unknown_coords = [name for name in coords if name not in vocab["coordinates"]]
    if unknown_coords:
        problems.append("unknown coordinates " + ", ".join(unknown_coords))
    names = roles.get("names") or []
    role_rows = roles.get("roles") or []
    score_rows = roles.get("scores") or []
    if len(role_rows) != len(roles.get("times_s") or []) or len(score_rows) != len(role_rows):
        problems.append("muscle role rows do not match times")
    if any(len(row) != len(names) for row in role_rows + score_rows):
        problems.append("muscle role width does not match names")
    allowed = {"prime_mover", "synergist", "stabilizer", "antagonist", "inactive"}
    unknown_muscles = [name for name in names if name not in vocab["muscles"]]
    if unknown_muscles:
        problems.append("unknown muscles " + ", ".join(unknown_muscles))
    if any(role not in allowed for row in role_rows for role in row):
        problems.append("unknown muscle role")
    load = emission["load"]
    if "direction_known" not in load or "description" not in load:
        problems.append("load is incomplete")
    confidence = emission["confidence"]
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        problems.append("confidence must be between 0 and 1")
    return problems


def _couple_side(group: list[str], roles: dict[str, str]) -> str:
    found = [roles.get(muscle, "inactive") for muscle in group]
    if any(role in ("prime_mover", "synergist") for role in found):
        return "mover"
    if any(role == "antagonist" for role in found):
        return "opposed"
    return "absent"


def _sign_violations(primes: list[str], action: dict, task_moments: dict) -> list[str]:
    violations = []
    for muscle in primes:
        signs = action["muscles"].get(muscle, {})
        agreed = False
        opposed = []
        for coord, required in task_moments.items():
            if required == 0:
                continue
            got = int(signs.get(coord, 0))
            if got == 0:
                continue
            if got == required:
                agreed = True
            else:
                opposed.append(f"{coord} sign {got:+d} against required {required:+d}")
        if opposed or not agreed:
            detail = "; ".join(opposed) if opposed else "no agreeing task coordinate"
            violations.append(f"{muscle} ({detail})")
    return violations


def _joint_visible(name: str, emission: dict, heldout: dict) -> bool:
    if name not in emission["joint_angles"]["coordinates"]:
        return False
    if name not in heldout.get("coordinates", []):
        return False
    flags = heldout.get("visible")
    if flags is None or name not in flags:
        return True
    flag = flags[name]
    if isinstance(flag, list):
        if not flag:
            return False
        return sum(bool(item) for item in flag) / len(flag) >= 0.7
    return bool(flag)


def _errors(name: str, emission_angles: dict, heldout: dict) -> list[float]:
    left_t, left_v = _series(emission_angles, name)
    right_t, right_v = _series(heldout, name)
    errors = []
    for time, value in zip(left_t, left_v):
        if time < right_t[0] or time > right_t[-1]:
            continue
        errors.append(abs(value - _interp(right_t, right_v, time)))
    return errors


def _series(block: dict, name: str) -> tuple[list[float], list[float]]:
    index = block["coordinates"].index(name)
    return list(block["times_s"]), [row[index] for row in block["values"]]


def _interp(times: list[float], values: list[float], time: float) -> float:
    if time <= times[0]:
        return values[0]
    if time >= times[-1]:
        return values[-1]
    for index in range(len(times) - 1):
        start, end = times[index], times[index + 1]
        if start <= time <= end:
            if end == start:
                return values[index]
            weight = (time - start) / (end - start)
            return values[index] + weight * (values[index + 1] - values[index])
    return values[-1]


def _unique(names: list[str]) -> list[str]:
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def _status(status: str, reason: str, **extra) -> dict:
    payload = {"status": status, "reason": reason}
    payload.update(extra)
    return payload


def _invalid(prototype_id: str, item_id: str, reason: str) -> dict:
    skip = _status("abstain", "Emission failed validation.")
    return {
        "prototype_id": prototype_id,
        "item_id": item_id,
        "overall": _status("invalid", reason),
        "legality": skip,
        "joint_path": skip,
        "muscle_role": skip,
        "negative_control": _status("not_applicable", "Emission failed validation."),
        "force_couple": _status("not_applicable", "Emission failed validation."),
    }


def _read(path: Path):
    return json.loads(path.read_text())


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    score_runs(ROOT / "runs", ROOT / "exam")


if __name__ == "__main__":
    main()
