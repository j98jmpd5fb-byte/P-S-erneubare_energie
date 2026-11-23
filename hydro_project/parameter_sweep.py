import itertools
from pathlib import Path

import pandas as pd

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.simulation import run_simulation
from src.strategy import SCENARIO_STRATEGIES
from src.plots import POSTER_DPI, save_pareto_frontier_plot


def get_parameter_grid():
    """Return the parameter grid for renewable-support strategy sweeps.

    Change these lists to tune the parameter sweep.
    """
    parameter_grid = {
        "min_surplus_mwh": [0.0],
        "min_renewable_fraction": [0.5],
        "safety_margin": [0.85, 0.95, 1.05],
        "low_quantile": [0.20],
        "high_quantile": [0.80, 0.85, 0.90],
        "round_trip_efficiency": [0.75],
        "seasonal_strength": [0.3, 0.4, 0.5, 0.6],
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
        import matplotlib.colors as mcolors
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
    
    x_col = "renewable_surplus_absorbed_MWh"
    y_col = "adjusted_total_profit_EUR"

    if y_col not in df.columns:
        print(f"Column '{y_col}' missing; cannot create tradeoff plot.")
        return

    fig, ax = plt.subplots(figsize=(12.5, 7.2), constrained_layout=True)

    # Point size = pumping-based deficit reduction, normalized to readable marker sizes.
    size_metric_col = (
        "pumping_based_deficit_reduction_MWh"
        if "pumping_based_deficit_reduction_MWh" in df.columns
        else "deficit_reduction_MWh"
    )
    size_metric = df[size_metric_col].fillna(0)
    color_metric_col = (
        "seasonal_strength"
        if "seasonal_strength" in df.columns and df["seasonal_strength"].nunique(dropna=True) > 1
        else "safety_margin"
    )
    color_values = df[color_metric_col].dropna()
    color_norm = (
        mcolors.Normalize(vmin=color_values.min(), vmax=color_values.max())
        if not color_values.empty and color_values.max() > color_values.min()
        else None
    )

    # Point size = pumping-based deficit reduction.
    size_values = size_metric

    if size_values.max() > size_values.min():
        sizes = 70 + 180 * (
            (size_values - size_values.min())
            / (size_values.max() - size_values.min())
        )
    else:
        sizes = pd.Series(140, index=df.index)

    unique_high_q = sorted(df["high_quantile"].dropna().unique())
    marker_cycle = ["o", "s", "^", "D", "X", "P"]

    scatter = None

    for idx, high_q in enumerate(unique_high_q):
        subset = df[df["high_quantile"] == high_q]

        if subset.empty:
            continue

        scatter = ax.scatter(
            subset[x_col] / 1e3,
            subset[y_col] / 1e6,
            c=subset[color_metric_col],
            s=sizes.loc[subset.index],
            cmap="viridis",
            norm=color_norm,
            alpha=0.75,
            edgecolor="black",
            linewidth=0.8,
            marker=marker_cycle[idx % len(marker_cycle)],
            label=f"high quantile = {high_q:.2f}",
        )

    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label(color_metric_col.replace("_", " ").title())

    ax.legend(
        title="Generation threshold",
        loc="upper left",
        bbox_to_anchor=(1.18, 1.0),
        frameon=False,
    )

    ax.set_title("Renewable-support tradeoff")
    ax.set_xlabel("Renewable surplus absorbed [GWh]")
    ax.set_ylabel("Profit [million EUR]")
    ax.set_xlim(
        (df["renewable_surplus_absorbed_MWh"].min() / 1e3) * 0.98,
        (df["renewable_surplus_absorbed_MWh"].max() / 1e3) * 1.18,
    )


    ax.grid(True, axis="y", linestyle="--", alpha=0.25)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=POSTER_DPI, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight")
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
    market_data["month"] = market_data["datetime"].dt.month

    monthly_avg_price = market_data.groupby("month")["price_EUR_per_MWh"].mean()
    year_avg_price = market_data["price_EUR_per_MWh"].mean()

    market_data["monthly_price_factor"] = (
        market_data["month"].map(monthly_avg_price) / year_avg_price
    )

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
            f"margin={params['safety_margin']}, "
            f"seasonal_strength={params['seasonal_strength']}"
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
            "shifted_pumped_energy_MWh": None,
            "pumping_based_deficit_reduction_MWh": None,
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
                    "shifted_pumped_energy_MWh": metrics.get("shifted_pumped_energy_MWh"),
                    "pumping_based_deficit_reduction_MWh": metrics.get("pumping_based_deficit_reduction_MWh"),
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
