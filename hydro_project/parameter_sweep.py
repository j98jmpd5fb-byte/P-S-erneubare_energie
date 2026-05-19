import itertools
from pathlib import Path

import pandas as pd

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.simulation import run_simulation
from src.strategy import SCENARIO_STRATEGIES
from src.plots import save_pareto_frontier_plot


def get_parameter_grid():
    """Return the parameter grid for renewable-support strategy sweeps.

    Change these lists to tune the parameter sweep.
    """
    parameter_grid = {
        "min_surplus_mwh": [0.0],
        "min_renewable_fraction": [0.3, 0.4, 0.5],
        "safety_margin": [0.90, 0.95, 1.00],
        "low_quantile": [0.20],
        "high_quantile": [0.70, 0.75, 0.80, 0.85],
        "round_trip_efficiency": [0.75],
    }

    keys = list(parameter_grid.keys())
    combinations = []
    for values in itertools.product(*(parameter_grid[key] for key in keys)):
        combo = dict(zip(keys, values))
        combinations.append(combo)

    return combinations


def create_tradeoff_plot(metrics_df: pd.DataFrame, output_path):
    """Create a tradeoff scatter plot for the renewable parameter sweep."""

    from pathlib import Path

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib is not installed; skipping tradeoff plot generation.")
        return

    output_path = Path(output_path)

    if metrics_df.empty:
        print("No successful sweep results available for plotting.")
        return

    df = metrics_df.copy()

    if "error" in df.columns:
        df = df[df["error"].isna()]

    if df.empty:
        print("No successful sweep results available for plotting.")
        return
    
    start_storage_MWh = 820040.0
    storage_value_EUR_per_MWh = 100.0

    if "storage_adjusted_profit_EUR" not in df.columns:
        df["storage_adjusted_profit_EUR"] = (
            df["total_profit_EUR"]
            + (df["final_storage_MWh"] - start_storage_MWh)
            * storage_value_EUR_per_MWh
        )

    x_col = "renewable_surplus_absorbed_MWh"
    y_col = "storage_adjusted_profit_EUR"

    fig, ax = plt.subplots(figsize=(11, 6))

    # Point size = deficit reduction, normalized to readable marker sizes
    size_metric = df["deficit_reduction_MWh"].fillna(0)

    if size_metric.max() > size_metric.min():
        sizes = 30 + 90 * (
            (size_metric - size_metric.min())
            / (size_metric.max() - size_metric.min())
        )
    else:
        sizes = pd.Series(90, index=df.index)

    color_metric = "safety_margin"

    unique_high_q = sorted(df["high_quantile"].dropna().unique())
    marker_cycle = ["o", "s", "^", "D", "X", "P"]

    scatter = None

    for idx, high_q in enumerate(unique_high_q):
        subset = df[df["high_quantile"] == high_q]

        if subset.empty:
            continue

        scatter = ax.scatter(
            subset[x_col],
            subset[y_col],
            c=subset[color_metric],
            s=sizes.loc[subset.index],
            cmap="viridis",
            alpha=0.70,
            edgecolor="black",
            linewidth=0.7,
            marker=marker_cycle[idx % len(marker_cycle)],
            label=f"high quantile = {high_q:.2f}",
        )

    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label("Safety margin")

    ax.legend(
        title="Generation threshold",
        loc="upper left",
        bbox_to_anchor=(1.18, 1.0),
    )

    ax.set_title("Renewable-support tradeoff: storage-adjusted profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [million MWh]")
    ax.set_ylabel("Storage-adjusted profit [million EUR]")
    ax.set_xlim(
        df["renewable_surplus_absorbed_MWh"].min() * 0.98,
        df["renewable_surplus_absorbed_MWh"].max() * 1.18,
    )


    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.2f}")
    )
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}")
    )

    ax.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_parameter_sweep():
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    parameter_sweep_dir = output_dir / "parameter_sweep"
    csv_dir = output_dir / "csv"
    parameter_sweep_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    market_data = load_market_data(data_dir / "simulation_input_2025.csv")
    market_data["grid_surplus_MWh"] = (
        market_data["total_production_MWh"]
        - market_data["total_consumption_MWh"]
    ).clip(lower=0)
    market_data["renewable_fraction"] = (
        market_data["renewable_MW"]
        / market_data["total_production_MW_avg"].replace(0, pd.NA)
    ).fillna(0)

    # Do not reuse a single plant instance across runs — load a fresh plant per combination
    # because `run_simulation` mutates `plant.storage_MWh` during the simulation.
    # We'll load a new `HydroPlant` for each parameter combination below.

    strategy_name = "renewable_surplus_plus_rolling_price"
    strategy = SCENARIO_STRATEGIES[strategy_name]

    grid = get_parameter_grid()
    total_combinations = len(grid)

    sweep_rows = []
    results_csv_path = csv_dir / "renewable_parameter_sweep.csv"

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
            "terminal_storage_value_EUR": None,
            "adjusted_total_profit_EUR": None,
            "total_pumped_MWh": None,
            "total_generated_MWh": None,
            "deficit_reduction_MWh": None,
            "surplus_absorbed_MWh": None,
            "renewable_surplus_absorbed_MWh": None,
            "final_storage_MWh": None,
            "error": None,
        }

        try:
            # create a fresh plant instance for this run so storage starts from the
            # configured initial storage each time
            plant_for_run = load_plant_parameters(data_dir / "plant_parameters.csv")

            results = run_simulation(
                market_data=market_data,
                plant=plant_for_run,
                strategy=strategy,
                strategy_kwargs=params,
                scenario=strategy_name,
            )
            metrics = calculate_metrics(results, plant=plant_for_run)

            row.update(
                {
                    "total_profit_EUR": metrics.get("total_profit_EUR"),
                    "terminal_storage_value_EUR": metrics.get("terminal_storage_value_EUR"),
                    "adjusted_total_profit_EUR": metrics.get("adjusted_total_profit_EUR"),
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

    plot_path = parameter_sweep_dir / "parameter_sweep_tradeoff.png"
    create_tradeoff_plot(sweep_df, plot_path)
    print(f"Saved parameter sweep CSV to {results_csv_path}")
    print(f"Saved tradeoff plot to {plot_path}")


def main():
    project_dir = Path(__file__).resolve().parent
    output_dir = project_dir / "outputs"
    parameter_sweep_dir = output_dir / "parameter_sweep"
    csv_dir = output_dir / "csv"
    parameter_sweep_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Run the sweep and save outputs into the organized outputs folder.
    # run_parameter_sweep()

    # If you want to regenerate only the plot from existing CSV, uncomment the lines below:
    sweep_df = pd.read_csv(csv_dir / "renewable_parameter_sweep.csv")
    plot_path = parameter_sweep_dir / "parameter_sweep_tradeoff.png"
    create_tradeoff_plot(sweep_df, plot_path)

    save_pareto_frontier_plot(
        sweep_df,
        Path("outputs") / "parameter_sweep" / "pareto_frontier.png",
    )


if __name__ == "__main__":
    main()
