"""Run every prototype, then the harness. The harness process is separate."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    steps = [
        [sys.executable, "-m", "prototypes.moment_arm.run"],
        [sys.executable, "-m", "prototypes.static_opt.run"],
        [sys.executable, "-m", "prototypes.opensim_arm.run"],
        [sys.executable, "-m", "harness.score"],
        [sys.executable, "-m", "harness.build_index"],
    ]
    for step in steps:
        print("+", " ".join(step[1:]))
        subprocess.run(step, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
