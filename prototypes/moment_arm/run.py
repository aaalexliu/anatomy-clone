from prototypes.engine import run_prototype
from prototypes.moment_arm.estimate import estimate


def main() -> None:
    run_prototype(
        prototype_id="moment_arm",
        display_name="Finite-difference moment arm",
        estimator="finite_difference_moment_arm",
        estimate=estimate,
    )


if __name__ == "__main__":
    main()
