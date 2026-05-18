import itertools
import os
from pathlib import Path

import pandas as pd

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.simulation import run_simulation
from src.strategy import SCENARIO_STRATEGIES


def get_parameter_grid():
    """Return the parameter grid for renewable-support strategy sweeps.

    Change these lists to tune the parameter sweep.
    """
    parameter_grid = {
        # Minimum renewable surplus needed before pumping is considered
        "min_surplus_mwh": [0.0, 100.0, 250.0],

        # Renewable share required to classify surplus as renewable support
        "min_renewable_fraction": [0.5, 0.7],

        # How much extra surplus is required before pumping aggressively
        "safety_margin": [1.00, 1.10, 1.25],

        # Price quantiles for rolling arbitrage thresholds
        "low_quantile": [0.20, 0.30],
        "high_quantile": [0.70, 0.80],

        # For now only test the realistic value we want to use finally
        "round_trip_efficiency": [0.75],
    }

    keys = list(parameter_grid.keys())
    combinations = []
    for values in itertools.product(*(parameter_grid[key] for key in keys)):
        combo = dict(zip(keys, values))
        combinations.append(combo)

    return combinations


def create_tradeoff_plot(metrics_df: pd.DataFrame, output_path: Path):
    """Create a tradeoff scatter plot for the renewable parameter sweep."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib is not installed; skipping tradeoff plot generation.")
        return

    if metrics_df.empty:
        print("No successful sweep results available for plotting.")
        return

    df = metrics_df.copy()

    if "error" in df.columns:
        df = df[df["error"].isna()]

    if df.empty:
        print("No successful sweep results available for plotting.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Normalize point sizes to a readable range
    size_metric = df["deficit_reduction_MWh"].fillna(0)

    if size_metric.max() > size_metric.min():
        sizes = 40 + 260 * (
            (size_metric - size_metric.min())
            / (size_metric.max() - size_metric.min())
        )
    else:
        sizes = 100

    # Since round_trip_efficiency is constant, color by a parameter that actually varies
    color_metric = df["safety_margin"]

    scatter = ax.scatter(
        df["renewable_surplus_absorbed_MWh"],
        df["total_profit_EUR"],
        c=color_metric,
        s=sizes,
        cmap="viridis",
        alpha=0.75,
        edgecolor="black",
        linewidth=0.4,
    )

    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Safety margin")

    ax.set_title("Renewable-support tradeoff: profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [MWh]")
    ax.set_ylabel("Total profit [million EUR]")

    # Format y-axis in million EUR
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}")
    )

    ax.grid(True, linestyle="--", alpha=0.3)

    ax.annotate(
        "Point size ~ deficit reduction",
        xy=(0.05, 0.95),
        xycoords="axes fraction",
        fontsize=9,
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.8},
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run_parameter_sweep():
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    market_data = load_market_data(data_dir / "simulation_input_2025.csv")
    market_data["grid_surplus_MWh"] = (
        market_data["total_production_MWh"]
        - market_data["total_consumption_MWh"]
    ).clip(lower=0)
    market_data["renewable_fraction"] = (
        market_data["renewable_MW"]
        / market_data["total_production_MW_avg"].replace(0, pd.NA)
    ).fillna(0)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")

    strategy_name = "renewable_surplus_plus_rolling_price"
    strategy = SCENARIO_STRATEGIES[strategy_name]

    grid = get_parameter_grid()
    total_combinations = len(grid)

    sweep_rows = []
    results_csv_path = output_dir / "renewable_parameter_sweep.csv"

    for index, params in enumerate(grid, start=1):
        combo_label = (
            f"min_surplus={params['min_surplus_mwh']}, "
            f"renewable_frac={params['min_renewable_fraction']}, "
            f"low_q={params['low_quantile']}, "
            f"high_q={params['high_quantile']}, "
            f"eff={params['round_trip_efficiency']}, "
            f"margin={params['safety_margin']}"
        )
        print(f"[{index}/{total_combinations}] Running {strategy_name} with {combo_label}")

        row = {
            "strategy_name": strategy_name,
            **params,
            "total_profit_EUR": None,
            "total_pumped_MWh": None,
            "total_generated_MWh": None,
            "deficit_reduction_MWh": None,
            "surplus_absorbed_MWh": None,
            "renewable_surplus_absorbed_MWh": None,
            "final_storage_MWh": None,
            "error": None,
        }

        try:
            results = run_simulation(
                market_data=market_data,
                plant=plant,
                strategy=strategy,
                strategy_kwargs=params,
                scenario=strategy_name,
            )
            metrics = calculate_metrics(results, plant=plant)

            row.update(
                {
                    "total_profit_EUR": metrics.get("total_profit_EUR"),
                    "total_pumped_MWh": metrics.get("total_pumped_MWh"),
                    "total_generated_MWh": metrics.get("total_generated_MWh"),
                    "deficit_reduction_MWh": metrics.get("deficit_reduction_MWh"),
                    "surplus_absorbed_MWh": metrics.get("surplus_absorbed_MWh"),
                    "renewable_surplus_absorbed_MWh": metrics.get("renewable_surplus_absorbed_MWh"),
                    "final_storage_MWh": metrics.get("final_storage_MWh"),
                }
            )
        except Exception as exc:
            row["error"] = str(exc)
            print(f"    Failed combination: {exc}")

        sweep_rows.append(row)

        # Save partial results after each combination so data is not lost.
        pd.DataFrame(sweep_rows).to_csv(results_csv_path, index=False)

    # Save final sweep results again after all simulations complete.
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(results_csv_path, index=False)

    plot_path = output_dir / "renewable_tradeoff_plot.png"
    create_tradeoff_plot(sweep_df, plot_path)
    print(f"Saved parameter sweep CSV to {results_csv_path}")
    print(f"Saved tradeoff plot to {plot_path}")


def main():
    # run_parameter_sweep()
    sweep_df = pd.read_csv("outputs/renewable_parameter_sweep.csv")
    plot_path = r"C:\Users\flori\repos\P-S-erneubare_energie\hydro_project\outputs\renewable_tradeoff_plot.png"
    create_tradeoff_plot(sweep_df, plot_path)


if __name__ == "__main__":
    main()
