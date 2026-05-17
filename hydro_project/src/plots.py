import os
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("/private/tmp/hydro_project_mpl")))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

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
    output_dir.mkdir(exist_ok=True)
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
    output_dir.mkdir(exist_ok=True)
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
    fig.savefig(output_dir / "storage_level_over_time.png", dpi=150)
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
    fig.savefig(output_dir / "cumulative_profit_over_time.png", dpi=150)
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
    fig.savefig(output_dir / "monthly_energy_summary.png", dpi=150)
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

    output_dir.mkdir(exist_ok=True)

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
    fig.savefig(output_dir / f"generation_vs_pumped_week_{start:%Y_%m_%d}.png", dpi=150)
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