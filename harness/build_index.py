"""Write runs/index.json from harness scores. Does not grade anything."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNER = "model estimate, not EMG"


def build_index(runs: Path, exam: Path) -> dict:
    catalog = json.loads((exam / "catalog.json").read_text())
    spec = {item["id"]: item for item in json.loads((exam / "score_spec.json").read_text())["items"]}
    prototypes = []
    if runs.exists():
        for path in sorted(runs.iterdir()):
            if not path.is_dir():
                continue
            meta_path = path / "prototype.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
            else:
                meta = {"id": path.name, "name": path.name}
            prototypes.append({"id": meta["id"], "name": meta.get("name", meta["id"])})
    items = []
    for item in catalog["items"]:
        frozen = spec.get(item["id"], {})
        items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "note": frozen.get("note", ""),
                "negative_control": bool(frozen.get("negative_control", False)),
            }
        )
    cells = []
    for prototype in prototypes:
        for item in items:
            score_path = runs / prototype["id"] / item["id"] / "score.json"
            if not score_path.exists():
                continue
            score = json.loads(score_path.read_text())
            cells.append(
                {
                    "prototype_id": prototype["id"],
                    "item_id": item["id"],
                    "status": score["overall"]["status"],
                    "reason": score["overall"]["reason"],
                    "scores": {
                        key: {"status": score[key]["status"], "reason": score[key]["reason"]}
                        for key in ("legality", "joint_path", "muscle_role", "negative_control", "force_couple")
                        if key in score
                    },
                    "muscle_role": {
                        "overlap": score["muscle_role"].get("overlap"),
                        "predicted_top5": score["muscle_role"].get("predicted_top5", []),
                        "reference_working": score["muscle_role"].get("reference_working", []),
                        "sign_violations": score["muscle_role"].get("sign_violations", []),
                    },
                    "score_path": f"{prototype['id']}/{item['id']}/score.json",
                    "emission_path": f"{prototype['id']}/{item['id']}/emission.json",
                    "playback_path": f"{prototype['id']}/{item['id']}/playback.json",
                }
            )
    return {"banner": BANNER, "prototypes": prototypes, "items": items, "cells": cells}


def main() -> None:
    payload = build_index(ROOT / "runs", ROOT / "exam")
    out = ROOT / "runs" / "index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out} ({len(payload['cells'])} cells)")


if __name__ == "__main__":
    main()
