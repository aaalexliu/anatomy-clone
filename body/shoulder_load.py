"""Which way MoBL-ARMS shoulder_rot externally rotates, read from the model.

The cable exercise resists external rotation: the forearm, elbow bent and
the upper arm at the side, moves away from the thorax midline. The sign is
whichever direction of shoulder_rot does that on this model. Muscle roles
then come from the same moment-arm rule as the other prototypes.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBL_PATH = ROOT / "models" / "opensim" / "MOBL_ARMS_41.osim"

# Moment arms are read on these coordinates. Only shoulder_rot carries the
# cable load. The others are held, so a muscle that cancels spill can be a
# stabilizer.
LOAD_COORDINATES = ("shoulder_rot", "elv_angle", "shoulder_elv", "elbow_flexion")

# Path-point parents in MoBL, and the Rajagopal body that wears that frame
# on the working side. Scapula and clavicle are part of the Rajagopal torso.
PARENT_TO_RAJ = {
    "thorax": "torso",
    "clavicle": "torso",
    "clavphant": "torso",
    "scapula": "torso",
    "scapphant": "torso",
    "humphant": "humerus",
    "humphant1": "humerus",
    "humerus": "humerus",
    "ulna": "ulna",
    "radius": "radius",
    "proximal_row": "hand",
    "hand": "hand",
}

SHOULDER_MUSCLES = (
    "DELT1",
    "DELT2",
    "DELT3",
    "SUPSP",
    "INFSP",
    "SUBSC",
    "TMIN",
    "TMAJ",
    "PECM1",
    "PECM2",
    "PECM3",
    "LAT1",
    "LAT2",
    "LAT3",
    "CORB",
    "TRIlong",
    "BIClong",
    "BICshort",
)

LABELS = {
    "DELT1": "Anterior deltoid",
    "DELT2": "Middle deltoid",
    "DELT3": "Posterior deltoid",
    "SUPSP": "Supraspinatus",
    "INFSP": "Infraspinatus",
    "SUBSC": "Subscapularis",
    "TMIN": "Teres minor",
    "TMAJ": "Teres major",
    "PECM1": "Pectoralis major, clavicular",
    "PECM2": "Pectoralis major, sternal",
    "PECM3": "Pectoralis major, abdominal",
    "LAT1": "Latissimus dorsi, thoracic",
    "LAT2": "Latissimus dorsi, lumbar",
    "LAT3": "Latissimus dorsi, iliac",
    "CORB": "Coracobrachialis",
    "TRIlong": "Triceps, long head",
    "BIClong": "Biceps, long head",
    "BICshort": "Biceps, short head",
}


def external_rotation_sign(model_path: Path | None = None) -> int:
    """Return +1 when increasing shoulder_rot swings the hand away from midline."""
    import opensim

    opensim.Logger.setLevelString("Off")
    model = opensim.Model(str(model_path or MOBL_PATH))
    state = model.initSystem()
    coords = model.getCoordinateSet()
    _set_deg(coords, state, "elbow_flexion", 90.0)
    _set_deg(coords, state, "elv_angle", 0.0)
    _set_deg(coords, state, "shoulder_elv", 0.0)
    lateral = _lateral_axis(model, state)
    low = _hand_lateral(model, state, coords, lateral, -30.0)
    high = _hand_lateral(model, state, coords, lateral, 30.0)
    if abs(high - low) < 1e-4:
        raise RuntimeError("shoulder_rot did not move the hand on MoBL-ARMS")
    return 1 if high > low else -1


def _set_deg(coords, state, name: str, degrees: float) -> None:
    coord = coords.get(name)
    radians = min(max(math.radians(degrees), coord.getRangeMin()), coord.getRangeMax())
    coord.setValue(state, radians)


def _lateral_axis(model, state):
    import numpy as np

    model.realizePosition(state)
    thorax = _origin(model, state, "thorax")
    humerus = _origin(model, state, "humerus")
    lateral = humerus - thorax
    lateral[1] = 0.0
    norm = np.linalg.norm(lateral)
    if norm < 1e-6:
        raise RuntimeError("MoBL humerus is not lateral of the thorax")
    return lateral / norm


def _hand_lateral(model, state, coords, lateral, degrees: float) -> float:
    import numpy as np

    _set_deg(coords, state, "shoulder_rot", degrees)
    model.realizePosition(state)
    hand = _origin(model, state, "hand")
    thorax = _origin(model, state, "thorax")
    return float(np.dot(hand - thorax, lateral))


def _origin(model, state, name: str):
    import numpy as np

    point = model.getBodySet().get(name).getTransformInGround(state).p()
    return np.array([point.get(0), point.get(1), point.get(2)], dtype=float)


def required_signs(external_sign: int) -> dict[str, int]:
    signs = {name: 0 for name in LOAD_COORDINATES}
    signs["shoulder_rot"] = external_sign
    return signs
