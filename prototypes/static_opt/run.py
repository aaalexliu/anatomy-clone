from prototypes.engine import run_prototype
from prototypes.static_opt.estimate import estimate


def main() -> None:
    run_prototype(
        prototype_id="static_opt",
        display_name="Static optimization",
        estimator="static_optimization",
        estimate=estimate,
    )


if __name__ == "__main__":
    main()
