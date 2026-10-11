"""Sample a scripted motion. Prototypes share this. The harness does not."""

from __future__ import annotations

from body.rig import COORDINATES


def _smooth(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def sample_motion(motion: dict) -> tuple[list[float], list[dict[str, float]]]:
    fps = int(motion["fps"])
    duration = float(motion["duration_s"])
    n = int(round(duration * fps))
    times = [i / fps for i in range(n + 1)]
    keys = sorted(motion["keyframes"], key=lambda row: row["t"])
    rows = []
    for t in times:
        angles = _at(keys, t)
        rows.append({name: float(angles.get(name, 0.0)) for name in COORDINATES})
    return times, rows


def _at(keys: list[dict], t: float) -> dict[str, float]:
    if t <= keys[0]["t"]:
        return keys[0]["angles_deg"]
    if t >= keys[-1]["t"]:
        return keys[-1]["angles_deg"]
    for left, right in zip(keys, keys[1:]):
        if left["t"] <= t <= right["t"]:
            span = right["t"] - left["t"]
            u = 0.0 if span == 0 else (t - left["t"]) / span
            s = _smooth(u)
            names = set(left["angles_deg"]) | set(right["angles_deg"])
            return {
                name: float(left["angles_deg"].get(name, 0.0))
                + (
                    float(right["angles_deg"].get(name, 0.0))
                    - float(left["angles_deg"].get(name, 0.0))
                )
                * s
                for name in names
            }
    return keys[-1]["angles_deg"]


def required_moment_signs(motion: dict) -> dict[str, int]:
    """Moment the muscles must produce.

    Concentric clips take the sign from the net joint travel. An external load
    (a squat, a cable) carries its own required signs. A joint that barely
    moves is held: its required moment is zero.
    """
    if motion["load_model"] == "external":
        raw = motion["load"]["required_moment_signs"]
        return {name: int(raw.get(name, 0)) for name in COORDINATES}
    if motion["load_model"] != "concentric":
        raise ValueError(f"unknown load_model {motion['load_model']}")
    start = motion["keyframes"][0]["angles_deg"]
    end = motion["keyframes"][-1]["angles_deg"]
    signs = {}
    for name in COORDINATES:
        delta = float(end.get(name, 0.0)) - float(start.get(name, 0.0))
        if abs(delta) < 8.0:
            signs[name] = 0
        else:
            signs[name] = 1 if delta > 0 else -1
    return signs
