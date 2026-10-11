"""Pose the official arm26 model and read muscle moment arms.

Heads of one anatomical muscle are averaged. Muscles and coordinates the
model does not have stay at zero so the rest of the vocab still lines up.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "opensim" / "arm26.osim"

# arm26 coordinate name -> vocab coordinate. Ranges match exam/limits/arm26.json.
POSE = {
    "shoulder_flexion": "r_shoulder_elev",
    "elbow_flexion": "r_elbow_flex",
}

# Mean of these heads is the vocab muscle's moment arm.
HEADS = {
    "biceps_brachii": ("BIClong", "BICshort"),
    "brachialis": ("BRA",),
    "triceps_brachii": ("TRIlong", "TRIlat", "TRImed"),
}


class Arm26:
    """One loaded model. computeMomentArm is the only source of the numbers."""

    def __init__(self, path: Path | None = None) -> None:
        import opensim

        model_path = Path(path) if path is not None else MODEL_PATH
        if not model_path.is_file():
            raise FileNotFoundError(f"arm26 model not found: {model_path}")
        self._opensim = opensim
        self.model = opensim.Model(str(model_path))
        self.state = self.model.initSystem()
        coordinates = self.model.getCoordinateSet()
        self._coords = {name: coordinates.get(name) for name in POSE.values()}
        muscles = self.model.getMuscles()
        self._heads = {
            vocab: tuple(muscles.get(head) for head in heads) for vocab, heads in HEADS.items()
        }

    def moment_arms(self, angles_deg: dict[str, float], muscle_names: list[str]) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
        """Return (moment arms in m/rad, posed degrees actually set on the model)."""
        from body.rig import COORDINATES

        posed = {}
        for vocab_name, osim_name in POSE.items():
            asked = float(angles_deg.get(vocab_name, 0.0))
            coord = self._coords[osim_name]
            radians = min(max(math.radians(asked), coord.getRangeMin()), coord.getRangeMax())
            coord.setValue(self.state, radians)
            posed[vocab_name] = math.degrees(radians)
        self.model.realizePosition(self.state)

        arms = {name: {coord: 0.0 for coord in COORDINATES} for name in muscle_names}
        for vocab_name, heads in self._heads.items():
            if vocab_name not in arms:
                continue
            for vocab_coord, osim_name in POSE.items():
                coord = self._coords[osim_name]
                samples = [float(head.computeMomentArm(self.state, coord)) for head in heads]
                arms[vocab_name][vocab_coord] = sum(samples) / len(samples)
        return arms, posed
