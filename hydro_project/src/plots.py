import os
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("/private/tmp/hydro_project_mpl")))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as mticker

def find_most_volatile_week(results):
    """Return the Monday start date of the week with highest price volatility."""

    data = results.copy()
    data["datetime"] = pd.to_datetime(data["datetime"])
    data = data.sort_values("datetime")

    data["week_start"] = data["datetime"].dt.to_period("W-MON").dt.start_time

    weekly_volatility = (
        data.groupby("week_start")["price_EUR_per_MWh"]
        .std()
        .dropna()
    )

    if weekly_volatility.empty:
        return None

    return weekly_volatility.idxmax().strftime("%Y-%m-%d")


def save_all_plots(results, output_dir):
    # Save scenario-specific operational plots in the organized operational_plots tree.
    output_dir.mkdir(parents=True, exist_ok=True)
    _plot_price(results, output_dir)
    _plot_price_thresholds(results, output_dir)
    _plot_demand_vs_production(results, output_dir)
    _plot_net_balance(results, output_dir)
    _plot_storage(results, output_dir)
    _plot_power(results, output_dir)
    _plot_actions(results, output_dir)
    _plot_cumulative_profit(results, output_dir)
    _plot_monthly_energy(results, output_dir)
    focus_weeks = [
        "2025-01-06",
        "2025-04-07",
        "2025-07-07",
        "2025-10-06",
    ]

    for start_date in focus_weeks:
        _plot_focus_week_dashboard(results, output_dir, start_date=start_date)

    _plot_natural_inflow(results, output_dir)
    _plot_spilled_inflow(results, output_dir)


def save_scenario_comparison_plot(metrics_summary, output_dir):
    # Save core comparison plots in the dedicated core_plots directory.
    output_dir.mkdir(parents=True, exist_ok=True)
    if metrics_summary.empty:
        return

    metrics = [
        "total_profit_EUR",
        "total_pumped_MWh",
        "total_generated_MWh",
        "final_storage_MWh",
    ]

    available = [metric for metric in metrics if metric in metrics_summary.columns]
    if not available:
        return

    fig, axes = plt.subplots(len(available), 1, figsize=(10, 3 * len(available)))

    if len(available) == 1:
        axes = [axes]

    for ax, metric in zip(axes, available):
        ax.bar(metrics_summary["scenario"], metrics_summary[metric])
        ax.set_title(metric)
        ax.set_ylabel(metric)
        ax.tick_params(axis="x", rotation=25)

    fig.tight_layout()
    fig.savefig(output_dir / "scenario_comparison.png", dpi=150)
    plt.close(fig)


def save_adjusted_profit_plot(metrics_summary, output_dir):
    # Save a core plot comparing adjusted profit across strategies.
    output_dir.mkdir(parents=True, exist_ok=True)
    if metrics_summary.empty or "adjusted_total_profit_EUR" not in metrics_summary.columns:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(metrics_summary["scenario"], metrics_summary["adjusted_total_profit_EUR"], color="tab:green")
    ax.set_title("Adjusted total profit across strategies")
    ax.set_ylabel("Adjusted profit [EUR]")
    ax.set_xlabel("Scenario")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "core_adjusted_total_profit.png", dpi=150)
    plt.close(fig)


def _plot_price(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["price_EUR_per_MWh"], color="tab:blue", label="Price")
    ax.set_title("Hourly electricity price")
    ax.set_ylabel("EUR/MWh")
    ax.set_xlabel("Time")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "price_over_time.png", dpi=150)
    plt.close(fig)


def _plot_price_thresholds(results, output_dir):
    if results["low_threshold"].dropna().empty and results["high_threshold"].dropna().empty:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["price_EUR_per_MWh"], color="tab:blue", label="Price")
    ax.plot(results["datetime"], results["low_threshold"], color="tab:green", linestyle="--", label="Low threshold")
    ax.plot(results["datetime"], results["high_threshold"], color="tab:red", linestyle="--", label="High threshold")
    ax.set_title("Price with thresholds")
    ax.set_ylabel("EUR/MWh")
    ax.set_xlabel("Time")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "price_thresholds_over_time.png", dpi=150)
    plt.close(fig)


def _plot_demand_vs_production(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["load_MW"], label="Load", color="tab:red")
    ax.plot(results["datetime"], results["production_MW"], label="Production", color="tab:blue")
    ax.set_title("Load vs production")
    ax.set_ylabel("MW")
    ax.set_xlabel("Time")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "load_vs_production.png", dpi=150)
    plt.close(fig)


def _plot_net_balance(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["net_balance_MW"], color="tab:purple")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Net balance (production - load)")
    ax.set_ylabel("MW")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "net_balance_over_time.png", dpi=150)
    plt.close(fig)


def _plot_storage(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["storage_MWh"], color="tab:green")
    ax.set_title("Storage level")
    ax.set_ylabel("MWh")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "yearly_storage_level.png", dpi=150)
    plt.close(fig)


def _plot_power(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["pump_MWh"], label="Pump power", color="tab:cyan")
    ax.plot(results["datetime"], results["generation_MWh"], label="Generation power", color="tab:orange")
    ax.set_title("Pumping and generation energy")
    ax.set_ylabel("MWh")
    ax.set_xlabel("Time")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "pump_generation_power_over_time.png", dpi=150)
    plt.close(fig)


def _plot_actions(results, output_dir):
    start = results["datetime"].min()
    end = start + timedelta(days=7)
    weekly_results = results[
        (results["datetime"] >= start) & (results["datetime"] < end)
    ]

    if weekly_results.empty:
        return

    action_to_value = {"pump": -1, "idle": 0, "generate": 1}
    action_values = weekly_results["action"].map(action_to_value)

    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.step(weekly_results["datetime"], action_values, where="mid", color="tab:purple")
    ax.set_title(
        "Hourly operation action "
        f"({start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d})"
    )
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["pump", "idle", "generate"])
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "hourly_action_plot.png", dpi=150)
    plt.close(fig)


def _plot_cumulative_profit(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        results["datetime"],
        results["profit_EUR"].cumsum(),
        color="tab:orange",
    )
    ax.set_title("Cumulative operating profit")
    ax.set_ylabel("EUR")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "yearly_cumulative_profit.png", dpi=150)
    plt.close(fig)


def _plot_monthly_energy(results, output_dir):
    if results["datetime"].empty:
        return
    monthly = results.copy()
    monthly["month"] = pd.to_datetime(monthly["datetime"]).dt.to_period("M")
    monthly = monthly.groupby("month")[['pump_MWh', 'generation_MWh']].sum()
    if monthly.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    monthly.plot(kind="bar", ax=ax)
    ax.set_title("Monthly pumped vs generated energy")
    ax.set_ylabel("MWh")
    ax.set_xlabel("Month")
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(output_dir / "monthly_energy_balance.png", dpi=150)
    plt.close(fig)


def _plot_focus_week_dashboard(results, output_dir, start_date="2025-01-06"):
    """Plot one selected week in detail to understand dispatch behavior."""

    data = results.copy()
    data["datetime"] = pd.to_datetime(data["datetime"])

    start = pd.to_datetime(start_date)
    end = start + timedelta(days=7)

    week = data[(data["datetime"] >= start) & (data["datetime"] < end)]

    if week.empty:
        return

    action_to_value = {"pump": -1, "idle": 0, "generate": 1}
    action_values = week["action"].map(action_to_value)

    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True)

    axes[0].plot(week["datetime"], week["price_EUR_per_MWh"], label="Price")
    if not week["low_threshold"].dropna().empty:
        axes[0].plot(week["datetime"], week["low_threshold"], linestyle="--", label="Low threshold")
    if not week["high_threshold"].dropna().empty:
        axes[0].plot(week["datetime"], week["high_threshold"], linestyle="--", label="High threshold")
    axes[0].set_ylabel("EUR/MWh")
    axes[0].set_title(f"Selected week dispatch dashboard: {start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d}")
    axes[0].legend()

    axes[1].plot(week["datetime"], week["storage_MWh"])
    axes[1].set_ylabel("Storage MWh")
    axes[1].set_title("Reservoir storage level")

    axes[2].plot(week["datetime"], week["pump_MWh"], label="Pumping")
    axes[2].plot(week["datetime"], week["generation_MWh"], label="Generation")
    axes[2].set_ylabel("MWh/h")
    axes[2].set_title("Pumping and generation")
    axes[2].legend()

    axes[3].step(week["datetime"], action_values, where="mid")
    axes[3].set_yticks([-1, 0, 1])
    axes[3].set_yticklabels(["pump", "idle", "generate"])
    axes[3].set_ylabel("Action")
    axes[3].set_title("Dispatch action")

    axes[3].set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / f"focus_week_dashboard_{start:%Y_%m_%d}.png", dpi=150)
    plt.close(fig)

def save_strategy_week_comparison_plot(
    generation_only_results,
    pumped_storage_results,
    output_dir,
    start_date="2025-01-06",
):
    """Compare generation-only hydropower and pumped-storage operation on the same week."""

    # Save representative weekly operational comparison plots in operational_plots/week_comparisons.
    output_dir.mkdir(parents=True, exist_ok=True)

    generation_only_data = generation_only_results.copy()
    pumped_storage_data = pumped_storage_results.copy()

    generation_only_data["datetime"] = pd.to_datetime(generation_only_data["datetime"])
    pumped_storage_data["datetime"] = pd.to_datetime(pumped_storage_data["datetime"])

    start = pd.to_datetime(start_date)
    end = start + timedelta(days=7)

    generation_only_week = generation_only_data[
        (generation_only_data["datetime"] >= start) & (generation_only_data["datetime"] < end)
    ]
    pumped_storage_week = pumped_storage_data[
        (pumped_storage_data["datetime"] >= start) & (pumped_storage_data["datetime"] < end)
    ]

    if generation_only_week.empty or pumped_storage_week.empty:
        return

    action_to_value = {"pump": -1, "idle": 0, "generate": 1}
    generation_only_action = generation_only_week["action"].map(action_to_value)
    pumped_storage_action = pumped_storage_week["action"].map(action_to_value)

    fig, axes = plt.subplots(5, 1, figsize=(13, 12), sharex=True)

    axes[0].plot(generation_only_week["datetime"], generation_only_week["price_EUR_per_MWh"], label="Price")
    axes[0].plot(generation_only_week["datetime"], generation_only_week["high_threshold"], linestyle="--", label="Generation-only high threshold")
    axes[0].plot(pumped_storage_week["datetime"], pumped_storage_week["low_threshold"], linestyle=":", label="Pumped-storage low threshold")
    axes[0].plot(pumped_storage_week["datetime"], pumped_storage_week["high_threshold"], linestyle=":", label="Pumped-storage high threshold")
    axes[0].set_ylabel("EUR/MWh")
    axes[0].set_title(
        f"Generation-only vs pumped-storage week: {start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d}"
    )
    axes[0].legend()

    axes[1].step(generation_only_week["datetime"], generation_only_action, where="mid")
    axes[1].set_yticks([-1, 0, 1])
    axes[1].set_yticklabels(["pump", "idle", "generate"])
    axes[1].set_ylabel("Gen-only")
    axes[1].set_title("Current hydropower operation: generation only")

    axes[2].step(pumped_storage_week["datetime"], pumped_storage_action, where="mid")
    axes[2].set_yticks([-1, 0, 1])
    axes[2].set_yticklabels(["pump", "idle", "generate"])
    axes[2].set_ylabel("Pumped")
    axes[2].set_title("Upgraded pumped-storage operation")

    axes[3].plot(generation_only_week["datetime"], generation_only_week["storage_MWh"], label="Generation-only storage")
    axes[3].plot(pumped_storage_week["datetime"], pumped_storage_week["storage_MWh"], label="Pumped-storage storage")
    axes[3].set_ylabel("MWh")
    axes[3].set_title("Storage comparison")
    axes[3].legend()

    axes[4].plot(generation_only_week["datetime"], generation_only_week["profit_EUR"].cumsum(), label="Generation-only cumulative profit")
    axes[4].plot(pumped_storage_week["datetime"], pumped_storage_week["profit_EUR"].cumsum(), label="Pumped-storage cumulative profit")
    axes[4].set_ylabel("EUR")
    axes[4].set_title("Cumulative profit during selected week")
    axes[4].legend()

    axes[4].set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / f"weekly_operation_comparison_{start:%Y_%m_%d}.png", dpi=150)
    plt.close(fig)
    
def _plot_natural_inflow(results, output_dir):
    """Plot natural inflow into the reservoir over time."""

    if "natural_inflow_MWh" not in results.columns:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["natural_inflow_MWh"])
    ax.set_title("Natural inflow into reservoir")
    ax.set_ylabel("MWh per hour")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "natural_inflow_over_time.png", dpi=150)
    plt.close(fig)


def _plot_spilled_inflow(results, output_dir):
    """Plot natural inflow that could not be stored because reservoir was full."""

    if "spilled_inflow_MWh" not in results.columns:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["spilled_inflow_MWh"])
    ax.set_title("Spilled natural inflow")
    ax.set_ylabel("MWh per hour")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "spilled_inflow_over_time.png", dpi=150)
    plt.close(fig)


def save_core_kpi_bar_plots(summary_df: pd.DataFrame, output_dir: Path):
    """
    Create core strategy comparison bar plots from the scenario summary table.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    df = summary_df.copy()

    # Cleaner names for plotting
    if "strategy" in df.columns:
        label_col = "strategy"
    elif "scenario" in df.columns:
        label_col = "scenario"
    elif "strategy_name" in df.columns:
        label_col = "strategy_name"
    else:
        raise ValueError("No strategy/scenario name column found.")

    df[label_col] = df[label_col].astype(str)

    metrics = {
        "total_profit_EUR": {
            "ylabel": "Total profit [million EUR]",
            "filename": "core_total_profit.png",
            "scale": 1e6,
        },
        "total_pumped_MWh": {
            "ylabel": "Total pumped energy [GWh]",
            "filename": "core_total_pumped.png",
            "scale": 1e3,
        },
        "total_generated_MWh": {
            "ylabel": "Total generated energy [GWh]",
            "filename": "core_total_generated.png",
            "scale": 1e3,
        },
        "deficit_reduction_MWh": {
            "ylabel": "Deficit reduction [GWh]",
            "filename": "core_deficit_reduction.png",
            "scale": 1e3,
        },
        "renewable_surplus_absorbed_MWh": {
            "ylabel": "Renewable surplus absorbed [GWh]",
            "filename": "core_renewable_surplus_absorbed.png",
            "scale": 1e3,
        },
    }

    for metric, config in metrics.items():
        if metric not in df.columns:
            print(f"Skipping {metric}: column not found.")
            continue

        fig, ax = plt.subplots(figsize=(10, 6))

        values = df[metric] / config["scale"]

        ax.bar(df[label_col], values)

        ax.set_title(metric.replace("_", " "))
        ax.set_ylabel(config["ylabel"])
        ax.set_xlabel("Strategy")
        ax.grid(axis="y", linestyle="--", alpha=0.3)

        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()

        fig.savefig(output_dir / config["filename"], dpi=150)
        plt.close(fig)


def save_profit_vs_renewable_absorption_plot(summary_df: pd.DataFrame, output_path: Path):
    """
    Plot total profit against renewable surplus absorbed.
    """

    df = summary_df.copy()

    x_col = "renewable_surplus_absorbed_MWh"
    y_col = "total_profit_EUR"

    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Required columns missing for profit vs renewable absorption plot.")

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.scatter(
        df[x_col],
        df[y_col],
        s=120,
        alpha=0.8,
        edgecolor="black",
        linewidth=0.6,
    )

    label_col = (
        "strategy"
        if "strategy" in df.columns
        else "scenario"
        if "scenario" in df.columns
        else "strategy_name"
    )

    for _, row in df.iterrows():
        ax.annotate(
            str(row[label_col]),
            xy=(row[x_col], row[y_col]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title("Profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [MWh]")
    ax.set_ylabel("Total profit [million EUR]")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}"))

    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_deficit_vs_renewable_absorption_plot(summary_df: pd.DataFrame, output_path: Path):
        """
        Plot deficit reduction against renewable surplus absorbed.
        """

        df = summary_df.copy()

        x_col = "renewable_surplus_absorbed_MWh"
        y_col = "deficit_reduction_MWh"

        if x_col not in df.columns or y_col not in df.columns:
            raise ValueError("Required columns missing for deficit vs renewable absorption plot.")

        fig, ax = plt.subplots(figsize=(9, 6))

        ax.scatter(
            df[x_col],
            df[y_col],
            s=120,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.6,
        )

        label_col = (
            "strategy"
            if "strategy" in df.columns
            else "scenario"
            if "scenario" in df.columns
            else "strategy_name"
        )

        for _, row in df.iterrows():
            ax.annotate(
                str(row[label_col]),
                xy=(row[x_col], row[y_col]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=8,
            )

        ax.set_title("Deficit reduction vs renewable surplus absorbed")
        ax.set_xlabel("Renewable surplus absorbed [MWh]")
        ax.set_ylabel("Deficit reduction [MWh]")

        ax.grid(True, linestyle="--", alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)

def save_relative_improvement_plot(
        summary_df: pd.DataFrame,
        output_path: Path,
        baseline_scenario: str = "generation_only_rolling_24h",
):
        """
        Plot relative improvement of each strategy compared to generation-only baseline.
        """

        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = summary_df.copy()

        if "scenario" not in df.columns:
            raise ValueError("summary_df must contain a 'scenario' column.")

        baseline_rows = df[df["scenario"] == baseline_scenario]

        if baseline_rows.empty:
            raise ValueError(f"Baseline scenario not found: {baseline_scenario}")

        baseline = baseline_rows.iloc[0]

        metrics = {
            "total_profit_EUR": "Raw profit",
            "adjusted_total_profit_EUR": "Adjusted profit",
            "deficit_reduction_MWh": "Deficit reduction",
            "renewable_surplus_absorbed_MWh": "Renewable surplus absorbed",
        }

        available_metrics = [m for m in metrics if m in df.columns]

        rows = []

        for _, row in df.iterrows():
            if row["scenario"] == baseline_scenario:
                continue

            for metric in available_metrics:
                base_value = baseline[metric]
                value = row[metric]

                if base_value == 0:
                    # For renewable surplus, generation-only baseline is probably zero.
                    # Use absolute difference instead of percent improvement.
                    improvement = value
                    unit = "absolute"
                else:
                    improvement = 100 * (value - base_value) / base_value
                    unit = "percent"

                rows.append(
                    {
                        "scenario": row["scenario"],
                        "metric": metrics[metric],
                        "improvement": improvement,
                        "unit": unit,
                    }
                )

        improvement_df = pd.DataFrame(rows)

        label_map = {
            "rolling_24h_price_arbitrage_max": "Arbitrage",
            "renewable_support_conservative": "Renew. conservative",
            "renewable_support_balanced": "Renew. balanced",
            "renewable_support_aggressive": "Renew. aggressive",
        }

        strategy_order = [
            "rolling_24h_price_arbitrage_max",
            "renewable_support_conservative",
            "renewable_support_balanced",
            "renewable_support_aggressive",
        ]

        improvement_df["strategy_label"] = improvement_df["scenario"].map(label_map)
        improvement_df["strategy_label"] = pd.Categorical(
            improvement_df["strategy_label"],
            categories=[label_map[s] for s in strategy_order],
            ordered=True,
        )

        if improvement_df.empty:
            return

        # Plot only percentage metrics here
        percent_df = improvement_df[improvement_df["unit"] == "percent"].copy()

        percent_df["strategy_label"] = percent_df["scenario"].map(label_map)
        percent_df["strategy_label"] = pd.Categorical(
            percent_df["strategy_label"],
            categories=[label_map[s] for s in strategy_order],
            ordered=True,
        )

        percent_df = percent_df.sort_values("strategy_label")

        fig, ax = plt.subplots(figsize=(11, 6))

        pivot = percent_df.pivot(
            index="strategy_label",
            columns="metric",
            values="improvement",
        )

        pivot.plot(kind="bar", ax=ax)

        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title("Relative improvement compared to generation-only")
        ax.set_ylabel("Improvement [%]")
        ax.set_xlabel("Strategy")
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.tick_params(axis="x", rotation=25)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)

        # Separate plot for renewable surplus absorbed, because baseline is zero
        absolute_df = improvement_df[improvement_df["unit"] == "absolute"]

        if not absolute_df.empty:
            fig, ax = plt.subplots(figsize=(10, 5))

            renewable_df = absolute_df[
                absolute_df["metric"] == "Renewable surplus absorbed"
            ]

            renewable_df = renewable_df.copy()
            renewable_df["strategy_label"] = renewable_df["scenario"].map(label_map)
            renewable_df["strategy_label"] = pd.Categorical(
                renewable_df["strategy_label"],
                categories=[label_map[s] for s in strategy_order],
                ordered=True,
            )
            renewable_df = renewable_df.sort_values("strategy_label")

            ax.bar(
                renewable_df["strategy_label"],
                renewable_df["improvement"] / 1e3,
            )

            ax.set_title("Renewable surplus absorbed compared to generation-only")
            ax.set_ylabel("Additional renewable surplus absorbed [GWh]")
            ax.set_xlabel("Strategy")
            ax.grid(axis="y", linestyle="--", alpha=0.3)
            ax.tick_params(axis="x", rotation=25)

            fig.tight_layout()
            fig.savefig(
                output_path.parent / "relative_renewable_surplus_absorbed.png",
                dpi=150,
            )
            plt.close(fig)

def save_storage_adjusted_profit_vs_renewable_absorption_plot(
    summary_df: pd.DataFrame,
    output_path: Path,
):
    df = summary_df.copy()

    x_col = "renewable_surplus_absorbed_MWh"
    y_col = "storage_adjusted_profit_EUR"

    if y_col not in df.columns:
        y_col = "adjusted_total_profit_EUR"

    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Required columns missing for storage-adjusted profit plot.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    label_map = {
        "generation_only_rolling_24h": "Generation only",
        "rolling_24h_price_arbitrage_max": "Arbitrage",
        "renewable_support_conservative": "Renew. conservative",
        "renewable_support_balanced": "Renew. balanced",
        "renewable_support_aggressive": "Renew. aggressive",
    }

    df["plot_label"] = df["scenario"].map(label_map).fillna(df["scenario"])

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.scatter(
        df[x_col],
        df[y_col],
        s=130,
        alpha=0.8,
        edgecolor="black",
        linewidth=0.6,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["plot_label"],
            xy=(row[x_col], row[y_col]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title("Storage-adjusted profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [GWh]")
    ax.set_ylabel("Storage-adjusted profit [million EUR]")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1e3:.0f}"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}"))

    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_pareto_frontier_plot(
    sweep_df: pd.DataFrame,
    output_path: Path,
):
    """
    Plot Pareto-optimal renewable sweep strategies.

    Pareto-optimal means:
    no other point has BOTH
    - higher profit
    - higher renewable absorption
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = sweep_df.copy()

    if "error" in df.columns:
        df = df[df["error"].isna()]

    if df.empty:
        return

    x_col = "renewable_surplus_absorbed_MWh" 

    start_storage_MWh = 820040.0
    storage_value_EUR_per_MWh = 100.0

    if "storage_adjusted_profit_EUR" not in df.columns:
        df["storage_adjusted_profit_EUR"] = (
            df["total_profit_EUR"]
            + (df["final_storage_MWh"] - start_storage_MWh)
            * storage_value_EUR_per_MWh
        )

    y_col = "storage_adjusted_profit_EUR"

    pareto_mask = []

    for i, row_i in df.iterrows():

        dominated = False

        for j, row_j in df.iterrows():

            if i == j:
                continue

            better_or_equal_x = row_j[x_col] >= row_i[x_col]
            better_or_equal_y = row_j[y_col] >= row_i[y_col]

            strictly_better = (
                row_j[x_col] > row_i[x_col]
                or row_j[y_col] > row_i[y_col]
            )

            if better_or_equal_x and better_or_equal_y and strictly_better:
                dominated = True
                break

        pareto_mask.append(not dominated)

    df["pareto_optimal"] = pareto_mask

    pareto_df = df[df["pareto_optimal"]].copy()

    print("\nPareto-optimal strategies:")
    print(
        pareto_df[
            [
                "high_quantile",
                "safety_margin",
                x_col,
                y_col,
            ]
        ]
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    # All points
    ax.scatter(
        df[x_col],
        df[y_col],
        color="lightgray",
        s=70,
        alpha=0.5,
        label="Dominated strategies",
    )

    # Pareto points
    ax.scatter(
        pareto_df[x_col],
        pareto_df[y_col],
        color="red",
        s=140,
        edgecolor="black",
        linewidth=0.8,
        label="Pareto frontier",
    )

    # Connect Pareto points
    pareto_df = pareto_df.sort_values(x_col)

    ax.plot(
        pareto_df[x_col],
        pareto_df[y_col],
        color="red",
        linewidth=2,
        alpha=0.8,
    )

    for _, row in pareto_df.iterrows():

        label = (
            f"HQ={row['high_quantile']:.2f}\n"
            f"SM={row['safety_margin']:.2f}"
        )

        ax.annotate(
            label,
            xy=(row[x_col], row[y_col]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title("Pareto frontier: profit vs renewable absorption")
    ax.set_title("Pareto frontier: storage-adjusted profit vs renewable absorption")
    ax.set_ylabel("Storage-adjusted profit [million EUR]")

    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x / 1e3:.0f}")
    )

    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}")
    )

    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_monthly_renewable_surplus_absorbed_plot(
    results: pd.DataFrame,
    output_path: Path,
):
    """
    Plot how much renewable surplus is absorbed in each month.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = results.copy()

    if "datetime" not in df.columns:
        raise ValueError("results must contain a datetime column.")

    if "renewable_surplus_absorbed_MWh" not in df.columns:
        raise ValueError("results must contain renewable_surplus_absorbed_MWh.")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df["month"] = df["datetime"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby("month")["renewable_surplus_absorbed_MWh"]
        .sum()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        monthly["month"],
        monthly["renewable_surplus_absorbed_MWh"] / 1e3,
    )

    ax.set_title("Monthly renewable surplus absorbed")
    ax.set_ylabel("Renewable surplus absorbed [GWh]")
    ax.set_xlabel("Month")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def save_deficit_before_after_week_plot(
    generation_only_results: pd.DataFrame,
    strategy_results: pd.DataFrame,
    output_path: Path,
    start_date: str = "2025-01-06",
):
    """
    Plot grid deficit before and after storage dispatch for one representative week.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    before = generation_only_results.copy()
    after = strategy_results.copy()

    before["datetime"] = pd.to_datetime(before["datetime"])
    after["datetime"] = pd.to_datetime(after["datetime"])

    start = pd.to_datetime(start_date)
    end = start + timedelta(days=7)

    before_week = before[
        (before["datetime"] >= start) & (before["datetime"] < end)
    ].copy()

    after_week = after[
        (after["datetime"] >= start) & (after["datetime"] < end)
    ].copy()

    if before_week.empty or after_week.empty:
        print(f"No data available for week starting {start_date}.")
        return

    # Deficit before storage: positive value when load > production
    before_week["deficit_before_MWh"] = (
        -before_week["net_balance_MW"]
    ).clip(lower=0)

    # Deficit after storage: original deficit reduced by storage generation
    after_week["deficit_after_MWh"] = (
        -after_week["net_balance_MW"] - after_week["generation_MWh"]
    ).clip(lower=0)

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        before_week["datetime"],
        before_week["deficit_before_MWh"],
        label="Deficit before storage",
        linewidth=1.8,
    )

    ax.plot(
        after_week["datetime"],
        after_week["deficit_after_MWh"],
        label="Deficit after storage",
        linewidth=1.8,
    )

    ax.fill_between(
        after_week["datetime"],
        after_week["deficit_after_MWh"],
        before_week["deficit_before_MWh"],
        where=before_week["deficit_before_MWh"] > after_week["deficit_after_MWh"],
        alpha=0.25,
        label="Deficit reduced",
    )

    ax.set_title(
        f"Grid deficit before and after storage dispatch "
        f"({start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d})"
    )
    ax.set_ylabel("Deficit [MWh per hour]")
    ax.set_xlabel("Time")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)