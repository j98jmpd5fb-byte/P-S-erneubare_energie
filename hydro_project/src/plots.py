import os
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("/private/tmp/hydro_project_mpl")))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as mticker

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42

POSTER_DPI = 300
LINEWIDTH = 2.4
GRID_ALPHA = 0.25

STRATEGY_LABELS = {
    "generation_only_rolling_24h": "Generation only",
    "rolling_24h_price_arbitrage": "Rolling 24h arbitrage",
    "rolling_24h_price_arbitrage_max": "Rolling 24h arbitrage",
    "renewable_support_conservative": "Renewable conservative",
    "renewable_support_balanced": "Renewable balanced",
    "renewable_support_aggressive": "Renewable aggressive",
    "renewable_surplus_plus_rolling_price": "Renewable support",
    "Generation only": "Generation only",
    "Arbitrage": "Rolling 24h arbitrage",
    "Renew. conservative": "Renewable conservative",
    "Renew. balanced": "Renewable balanced",
    "Renew. aggressive": "Renewable aggressive",
}

STRATEGY_COLORS = {
    "Generation only": "#7A7A7A",
    "Rolling 24h arbitrage": "#1F77B4",
    "Renewable conservative": "#006D2C",
    "Renewable balanced": "#2CA25F",
    "Renewable aggressive": "#D94801",
    "Renewable support": "#2CA25F",
}

PLOT_COLORS = {
    "price": "#1F77B4",
    "low_threshold": "#2CA25F",
    "high_threshold": "#D94801",
    "seasonal_threshold": "#6A51A3",
    "pump": "#1F77B4",
    "generation": "#D94801",
    "storage": "#2CA25F",
    "deficit": "#CB181D",
    "reduced": "#74C476",
    "dominated": "#CFCFCF",
    "pareto": "#D7191C",
}

plt.rcParams.update(
    {
        "figure.dpi": POSTER_DPI,
        "savefig.dpi": POSTER_DPI,
        "font.size": 13,
        "axes.titlesize": 18,
        "axes.labelsize": 15,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "legend.title_fontsize": 12,
        "lines.linewidth": LINEWIDTH,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _strategy_label(value):
    return STRATEGY_LABELS.get(str(value), str(value).replace("_", " ").title())


def _strategy_color(value):
    return STRATEGY_COLORS.get(_strategy_label(value), "#4D4D4D")


def _strategy_labels(series):
    return series.astype(str).map(_strategy_label)


def _strategy_colors(series):
    return [_strategy_color(value) for value in series.astype(str)]


def _apply_axis_style(ax):
    ax.grid(True, axis="y", linestyle="--", alpha=GRID_ALPHA)
    if isinstance(ax.yaxis.get_major_formatter(), mticker.ScalarFormatter):
        ax.ticklabel_format(style="plain", axis="y", useOffset=False)


def save_figure_with_vector_copy(fig, output_path, dpi=300):
    output_path = Path(output_path)

    # Keep original PNG output path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path.with_suffix(".png"), dpi=dpi, bbox_inches="tight")

    output_parts_lower = [part.lower() for part in output_path.parts]
    output_stem = output_path.stem.lower()
    should_save_svg = (
        "core_plots" in output_parts_lower
        or (
            "operational_plots" in output_parts_lower
            and output_stem.startswith("monthly_renewable_surplus_absorbed")
        )
        or ("parameter_sweep" in output_parts_lower and output_stem == "pareto_frontier")
    )

    if not should_save_svg:
        return

    # Save SVG copy into separate outputs_vek folder
    try:
        relative_path = output_path.relative_to("outputs")
        vector_base = Path("outputs_vek") / relative_path
    except ValueError:
        output_parts = output_path.parts
        outputs_indexes = [
            index for index, part in enumerate(output_parts) if part.lower() == "outputs"
        ]
        if outputs_indexes and outputs_indexes[-1] < len(output_parts) - 1:
            outputs_index = outputs_indexes[-1]
            relative_path = Path(*output_parts[outputs_index + 1:])
            outputs_parent = Path(*output_parts[:outputs_index])
            vector_base = outputs_parent / "outputs_vek" / relative_path
        else:
            vector_base = Path("outputs_vek") / output_path.name

    vector_base.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(vector_base.with_suffix(".svg"), bbox_inches="tight")


def _save_figure(fig, output_path, pdf=True):
    save_figure_with_vector_copy(fig, output_path, dpi=POSTER_DPI)
    plt.close(fig)


def _format_million_eur(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1e6:.0f}"))


def _format_gwh_axis(axis):
    axis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1e3:.0f}"))


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

    labels = _strategy_labels(metrics_summary["scenario"])
    colors = _strategy_colors(metrics_summary["scenario"])
    fig, axes = plt.subplots(
        len(available),
        1,
        figsize=(13, 4.2 * len(available)),
        constrained_layout=True,
    )

    if len(available) == 1:
        axes = [axes]

    metric_labels = {
        "total_profit_EUR": ("Profit [million EUR]", 1e6),
        "total_pumped_MWh": ("Pumped energy [GWh]", 1e3),
        "total_generated_MWh": ("Generated energy [GWh]", 1e3),
        "final_storage_MWh": ("Final storage [GWh]", 1e3),
    }

    for ax, metric in zip(axes, available):
        ylabel, scale = metric_labels.get(metric, (metric.replace("_", " "), 1.0))
        ax.bar(labels, metrics_summary[metric] / scale, color=colors, edgecolor="black", linewidth=0.6)
        ax.set_title(ylabel.replace(" [", "\n["))
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=20)
        _apply_axis_style(ax)

    _save_figure(fig, output_dir / "scenario_comparison.png")


def save_adjusted_profit_plot(metrics_summary, output_dir):
    # Save a core plot comparing adjusted profit across strategies.
    output_dir.mkdir(parents=True, exist_ok=True)
    if metrics_summary.empty or "adjusted_total_profit_EUR" not in metrics_summary.columns:
        return

    labels = _strategy_labels(metrics_summary["scenario"])
    colors = _strategy_colors(metrics_summary["scenario"])
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    ax.bar(labels, metrics_summary["adjusted_total_profit_EUR"] / 1e6, color=colors, edgecolor="black", linewidth=0.6)
    ax.set_title("Storage-adjusted profit")
    ax.set_ylabel("Profit [million EUR]")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=30)
    _apply_axis_style(ax)
    _save_figure(fig, output_dir / "core_adjusted_total_profit.png")


def _plot_price(results, output_dir):
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["price_EUR_per_MWh"], color=PLOT_COLORS["price"], label="Electricity price")
    ax.set_title("Hourly electricity price")
    ax.set_ylabel("Electricity price [EUR/MWh]")
    ax.set_xlabel("Time")
    ax.legend(frameon=False)
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "price_over_time.png")


def _plot_price_thresholds(results, output_dir):
    if results["low_threshold"].dropna().empty and results["high_threshold"].dropna().empty:
        return

    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["price_EUR_per_MWh"], color=PLOT_COLORS["price"], label="Electricity price")
    ax.plot(results["datetime"], results["low_threshold"], color=PLOT_COLORS["low_threshold"], linestyle="--", label="Pumping threshold")
    ax.plot(results["datetime"], results["high_threshold"], color=PLOT_COLORS["high_threshold"], linestyle="--", label="Generation threshold")
    if "seasonal_high_threshold" in results.columns and not results["seasonal_high_threshold"].dropna().empty:
        ax.plot(
            results["datetime"],
            results["seasonal_high_threshold"],
            color=PLOT_COLORS["seasonal_threshold"],
            linestyle="-.",
            alpha=0.85,
            label="Seasonal generation threshold",
        )
    ax.set_title("Electricity price and dispatch thresholds")
    ax.set_ylabel("Electricity price [EUR/MWh]")
    ax.set_xlabel("Time")
    ax.legend(frameon=False, ncol=2)
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "price_thresholds_over_time.png")


def _plot_demand_vs_production(results, output_dir):
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["load_MW"], label="Load", color="#CB181D")
    ax.plot(results["datetime"], results["production_MW"], label="Production", color="#2171B5")
    ax.set_title("Load vs production")
    ax.set_ylabel("MW")
    ax.set_xlabel("Time")
    ax.legend(frameon=False)
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "load_vs_production.png")


def _plot_net_balance(results, output_dir):
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["net_balance_MW"], color="#6A51A3")
    ax.axhline(0, color="black", linewidth=1.2)
    ax.set_title("Net balance (production - load)")
    ax.set_ylabel("MW")
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "net_balance_over_time.png")


def _plot_storage(results, output_dir):
    storage_pct = results["storage_MWh"] / results["storage_MWh"].max() * 100
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], storage_pct, color=PLOT_COLORS["storage"])
    ax.fill_between(results["datetime"], storage_pct, color=PLOT_COLORS["storage"], alpha=0.18)
    ax.set_title("Storage level")
    ax.set_ylabel("Storage level [%]")
    ax.set_xlabel("Time")
    ax.set_ylim(0, 105)
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "yearly_storage_level.png")


def _plot_power(results, output_dir):
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.fill_between(results["datetime"], results["pump_MWh"], color=PLOT_COLORS["pump"], alpha=0.25, label="Pumped energy")
    ax.plot(results["datetime"], results["pump_MWh"], color=PLOT_COLORS["pump"], alpha=0.9)
    ax.fill_between(results["datetime"], results["generation_MWh"], color=PLOT_COLORS["generation"], alpha=0.25, label="Generated energy")
    ax.plot(results["datetime"], results["generation_MWh"], color=PLOT_COLORS["generation"], alpha=0.9)
    ax.set_title("Pumping and generation energy")
    ax.set_ylabel("Energy [MWh/h]")
    ax.set_xlabel("Time")
    ax.legend(frameon=False)
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "pump_generation_power_over_time.png")


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

    fig, ax = plt.subplots(figsize=(13, 4.5), constrained_layout=True)
    ax.step(weekly_results["datetime"], action_values, where="mid", color="#6A51A3")
    ax.fill_between(
        weekly_results["datetime"],
        0,
        action_values,
        where=action_values < 0,
        step="mid",
        color=PLOT_COLORS["pump"],
        alpha=0.22,
    )
    ax.fill_between(
        weekly_results["datetime"],
        0,
        action_values,
        where=action_values > 0,
        step="mid",
        color=PLOT_COLORS["generation"],
        alpha=0.22,
    )
    ax.set_title(
        "Hourly operation action "
        f"({start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d})"
    )
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["pump", "idle", "generate"])
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "hourly_action_plot.png")


def _plot_cumulative_profit(results, output_dir):
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(
        results["datetime"],
        results["profit_EUR"].cumsum() / 1e6,
        color=PLOT_COLORS["generation"],
    )
    ax.set_title("Cumulative operating profit")
    ax.set_ylabel("Profit [million EUR]")
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "yearly_cumulative_profit.png")


def _plot_monthly_energy(results, output_dir):
    if results["datetime"].empty:
        return
    monthly = results.copy()
    monthly["month"] = pd.to_datetime(monthly["datetime"]).dt.to_period("M")
    monthly = monthly.groupby("month")[['pump_MWh', 'generation_MWh']].sum()
    if monthly.empty:
        return

    fig, ax = plt.subplots(figsize=(13, 5.5), constrained_layout=True)
    (monthly / 1e3).plot(
        kind="bar",
        ax=ax,
        color=[PLOT_COLORS["pump"], PLOT_COLORS["generation"]],
        edgecolor="black",
        linewidth=0.5,
    )
    ax.set_title("Monthly pumped vs generated energy")
    ax.set_ylabel("Energy [GWh]")
    ax.set_xlabel("Month")
    ax.legend(["Pumped energy", "Generated energy"], frameon=False)
    _apply_axis_style(ax)
    fig.autofmt_xdate(rotation=30)
    _save_figure(fig, output_dir / "monthly_energy_balance.png")


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

    storage_pct = week["storage_MWh"] / data["storage_MWh"].max() * 100

    fig, axes = plt.subplots(4, 1, figsize=(15, 11), sharex=True, constrained_layout=True)

    axes[0].plot(week["datetime"], week["price_EUR_per_MWh"], color=PLOT_COLORS["price"], label="Electricity price")
    if not week["low_threshold"].dropna().empty:
        axes[0].plot(week["datetime"], week["low_threshold"], color=PLOT_COLORS["low_threshold"], linestyle="--", label="Pumping threshold")
    if not week["high_threshold"].dropna().empty:
        axes[0].plot(week["datetime"], week["high_threshold"], color=PLOT_COLORS["high_threshold"], linestyle="--", label="Generation threshold")
    if "seasonal_high_threshold" in week.columns and not week["seasonal_high_threshold"].dropna().empty:
        axes[0].plot(week["datetime"], week["seasonal_high_threshold"], color=PLOT_COLORS["seasonal_threshold"], linestyle="-.", label="Seasonal generation threshold")
    axes[0].set_ylabel("Electricity price [EUR/MWh]")
    axes[0].set_title(f"Weekly dispatch dashboard: {start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d}")
    axes[0].legend(frameon=False, ncol=2)

    axes[1].plot(week["datetime"], storage_pct, color=PLOT_COLORS["storage"])
    axes[1].fill_between(week["datetime"], storage_pct, color=PLOT_COLORS["storage"], alpha=0.18)
    axes[1].set_ylabel("Storage level [%]")
    axes[1].set_ylim(0, 105)
    axes[1].set_title("Reservoir storage")

    axes[2].fill_between(week["datetime"], week["pump_MWh"], color=PLOT_COLORS["pump"], alpha=0.25, label="Pumped energy")
    axes[2].plot(week["datetime"], week["pump_MWh"], color=PLOT_COLORS["pump"])
    axes[2].fill_between(week["datetime"], week["generation_MWh"], color=PLOT_COLORS["generation"], alpha=0.25, label="Generated energy")
    axes[2].plot(week["datetime"], week["generation_MWh"], color=PLOT_COLORS["generation"])
    axes[2].set_ylabel("Energy [MWh/h]")
    axes[2].set_title("Pumping and generation")
    axes[2].legend(frameon=False)

    axes[3].step(week["datetime"], action_values, where="mid", color="#6A51A3")
    axes[3].fill_between(week["datetime"], 0, action_values, where=action_values < 0, step="mid", color=PLOT_COLORS["pump"], alpha=0.22)
    axes[3].fill_between(week["datetime"], 0, action_values, where=action_values > 0, step="mid", color=PLOT_COLORS["generation"], alpha=0.22)
    axes[3].set_yticks([-1, 0, 1])
    axes[3].set_yticklabels(["pump", "idle", "generate"])
    axes[3].set_ylabel("Action")
    axes[3].set_title("Dispatch action")

    for ax in axes:
        _apply_axis_style(ax)

    axes[3].set_xlabel("Time")
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / f"focus_week_dashboard_{start:%Y_%m_%d}.png")

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

    gen_storage_pct = generation_only_week["storage_MWh"] / generation_only_data["storage_MWh"].max() * 100
    pump_storage_pct = pumped_storage_week["storage_MWh"] / pumped_storage_data["storage_MWh"].max() * 100

    fig, axes = plt.subplots(5, 1, figsize=(15, 13), sharex=True, constrained_layout=True)

    axes[0].plot(generation_only_week["datetime"], generation_only_week["price_EUR_per_MWh"], color=PLOT_COLORS["price"], label="Electricity price")
    axes[0].plot(generation_only_week["datetime"], generation_only_week["high_threshold"], color=STRATEGY_COLORS["Generation only"], linestyle="--", label="Generation-only threshold")
    axes[0].plot(pumped_storage_week["datetime"], pumped_storage_week["low_threshold"], color=PLOT_COLORS["low_threshold"], linestyle=":", label="Pumping threshold")
    axes[0].plot(pumped_storage_week["datetime"], pumped_storage_week["high_threshold"], color=PLOT_COLORS["high_threshold"], linestyle=":", label="Generation threshold")
    axes[0].set_ylabel("Electricity price [EUR/MWh]")
    axes[0].set_title(
        f"Weekly operation comparison: {start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d}"
    )
    axes[0].legend(frameon=False, ncol=2)

    axes[1].step(generation_only_week["datetime"], generation_only_action, where="mid", color=STRATEGY_COLORS["Generation only"])
    axes[1].fill_between(generation_only_week["datetime"], 0, generation_only_action, where=generation_only_action > 0, step="mid", color=STRATEGY_COLORS["Generation only"], alpha=0.25)
    axes[1].set_yticks([-1, 0, 1])
    axes[1].set_yticklabels(["pump", "idle", "generate"])
    axes[1].set_ylabel("Generation only")
    axes[1].set_title("Generation-only operation")

    axes[2].step(pumped_storage_week["datetime"], pumped_storage_action, where="mid", color=STRATEGY_COLORS["Rolling 24h arbitrage"])
    axes[2].fill_between(pumped_storage_week["datetime"], 0, pumped_storage_action, where=pumped_storage_action < 0, step="mid", color=PLOT_COLORS["pump"], alpha=0.22)
    axes[2].fill_between(pumped_storage_week["datetime"], 0, pumped_storage_action, where=pumped_storage_action > 0, step="mid", color=PLOT_COLORS["generation"], alpha=0.22)
    axes[2].set_yticks([-1, 0, 1])
    axes[2].set_yticklabels(["pump", "idle", "generate"])
    axes[2].set_ylabel("Pumped storage")
    axes[2].set_title("Rolling 24h arbitrage operation")

    axes[3].plot(generation_only_week["datetime"], gen_storage_pct, color=STRATEGY_COLORS["Generation only"], label="Generation only")
    axes[3].plot(pumped_storage_week["datetime"], pump_storage_pct, color=STRATEGY_COLORS["Rolling 24h arbitrage"], label="Rolling 24h arbitrage")
    axes[3].fill_between(pumped_storage_week["datetime"], pump_storage_pct, color=STRATEGY_COLORS["Rolling 24h arbitrage"], alpha=0.12)
    axes[3].set_ylabel("Storage level [%]")
    axes[3].set_ylim(0, 105)
    axes[3].set_title("Storage comparison")
    axes[3].legend(frameon=False)

    axes[4].plot(generation_only_week["datetime"], generation_only_week["profit_EUR"].cumsum() / 1e6, color=STRATEGY_COLORS["Generation only"], label="Generation only")
    axes[4].plot(pumped_storage_week["datetime"], pumped_storage_week["profit_EUR"].cumsum() / 1e6, color=STRATEGY_COLORS["Rolling 24h arbitrage"], label="Rolling 24h arbitrage")
    axes[4].set_ylabel("Profit [million EUR]")
    axes[4].set_title("Cumulative profit during selected week")
    axes[4].legend(frameon=False)

    for ax in axes:
        _apply_axis_style(ax)

    axes[4].set_xlabel("Time")
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / f"weekly_operation_comparison_{start:%Y_%m_%d}.png")
    
def _plot_natural_inflow(results, output_dir):
    """Plot natural inflow into the reservoir over time."""

    if "natural_inflow_MWh" not in results.columns:
        return

    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["natural_inflow_MWh"], color=PLOT_COLORS["storage"])
    ax.set_title("Natural inflow into reservoir")
    ax.set_ylabel("Energy [MWh/h]")
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "natural_inflow_over_time.png")


def _plot_spilled_inflow(results, output_dir):
    """Plot natural inflow that could not be stored because reservoir was full."""

    if "spilled_inflow_MWh" not in results.columns:
        return

    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.plot(results["datetime"], results["spilled_inflow_MWh"], color=PLOT_COLORS["generation"])
    ax.set_title("Spilled natural inflow")
    ax.set_ylabel("Energy [MWh/h]")
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    fig.autofmt_xdate()
    _save_figure(fig, output_dir / "spilled_inflow_over_time.png")


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
    df["plot_label"] = _strategy_labels(df[label_col])
    colors = _strategy_colors(df[label_col])

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
        "pumping_based_deficit_reduction_MWh": {
            "ylabel": "Potential import reduction from pumped storage [GWh]",
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

        fig, ax = plt.subplots(figsize=(12, 6.5), constrained_layout=True)

        values = df[metric] / config["scale"]

        ax.bar(df["plot_label"], values, color=colors, edgecolor="black", linewidth=0.6)

        ax.set_title(config["ylabel"].split("[")[0].strip())
        ax.set_ylabel(config["ylabel"])
        ax.set_xlabel("")
        _apply_axis_style(ax)

        ax.tick_params(axis="x", rotation=20)

        _save_figure(fig, output_dir / config["filename"])


def save_profit_vs_renewable_absorption_plot(summary_df: pd.DataFrame, output_path: Path):
    """
    Plot total profit against renewable surplus absorbed.
    """

    df = summary_df.copy()

    x_col = "renewable_surplus_absorbed_MWh"
    y_col = "total_profit_EUR"

    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Required columns missing for profit vs renewable absorption plot.")

    label_col = (
        "strategy"
        if "strategy" in df.columns
        else "scenario"
        if "scenario" in df.columns
        else "strategy_name"
    )
    labels = _strategy_labels(df[label_col])
    colors = _strategy_colors(df[label_col])

    fig, ax = plt.subplots(figsize=(10.5, 7), constrained_layout=True)

    ax.scatter(
        df[x_col] / 1e3,
        df[y_col] / 1e6,
        s=180,
        color=colors,
        alpha=0.8,
        edgecolor="black",
        linewidth=0.8,
    )

    for label, (_, row) in zip(labels, df.iterrows()):
        ax.annotate(
            label,
            xy=(row[x_col] / 1e3, row[y_col] / 1e6),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=11,
        )

    ax.set_title("Profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [GWh]")
    ax.set_ylabel("Profit [million EUR]")

    _apply_axis_style(ax)
    _save_figure(fig, output_path)


def save_deficit_vs_renewable_absorption_plot(summary_df: pd.DataFrame, output_path: Path):
        """
        Plot pumping-based deficit reduction against renewable surplus absorbed.
        """

        df = summary_df.copy()

        x_col = "renewable_surplus_absorbed_MWh"
        y_col = "pumping_based_deficit_reduction_MWh"

        if x_col not in df.columns or y_col not in df.columns:
            raise ValueError("Required columns missing for deficit vs renewable absorption plot.")

        label_col = (
            "strategy"
            if "strategy" in df.columns
            else "scenario"
            if "scenario" in df.columns
            else "strategy_name"
        )
        labels = _strategy_labels(df[label_col])
        colors = _strategy_colors(df[label_col])

        fig, ax = plt.subplots(figsize=(10.5, 7), constrained_layout=True)

        ax.scatter(
            df[x_col] / 1e3,
            df[y_col] / 1e3,
            s=180,
            color=colors,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.8,
        )

        for label, (_, row) in zip(labels, df.iterrows()):
            ax.annotate(
                label,
                xy=(row[x_col] / 1e3, row[y_col] / 1e3),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=11,
            )

        ax.set_title("Pumping-based deficit reduction vs renewable surplus absorbed")
        ax.set_xlabel("Renewable surplus absorbed [GWh]")
        ax.set_ylabel("Potential import reduction from pumped storage [GWh]")

        _apply_axis_style(ax)
        _save_figure(fig, output_path)

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
            "pumping_based_deficit_reduction_MWh": "Pumping-based deficit reduction",
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
            "rolling_24h_price_arbitrage_max": "Rolling 24h arbitrage",
            "renewable_support_conservative": "Renewable conservative",
            "renewable_support_balanced": "Renewable balanced",
            "renewable_support_aggressive": "Renewable aggressive",
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

        fig, ax = plt.subplots(figsize=(13, 7), constrained_layout=True)

        pivot = percent_df.pivot(
            index="strategy_label",
            columns="metric",
            values="improvement",
        )

        pivot.plot(kind="bar", ax=ax, width=0.78)

        for container in ax.containers:
            labels = [f"{value.get_height():.0f}%" if value.get_height() == value.get_height() else "" for value in container]
            ax.bar_label(container, labels=labels, padding=3, fontsize=10, rotation=90)

        ax.axhline(0, color="black", linewidth=1.2)
        ax.set_title("Improvement relative to generation-only operation")
        ax.set_ylabel("Improvement [%]")
        ax.set_xlabel("")
        ax.legend(frameon=False, ncol=2)
        _apply_axis_style(ax)
        ax.tick_params(axis="x", rotation=15)

        _save_figure(fig, output_path)

        # Separate plot for renewable surplus absorbed, because baseline is zero
        absolute_df = improvement_df[improvement_df["unit"] == "absolute"]

        if not absolute_df.empty:
            fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)

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

            bars = ax.bar(
                renewable_df["strategy_label"],
                renewable_df["improvement"] / 1e3,
                color=[_strategy_color(value) for value in renewable_df["strategy_label"].astype(str)],
                edgecolor="black",
                linewidth=0.6,
            )
            ax.bar_label(bars, labels=[f"{bar.get_height():.0f}" for bar in bars], padding=3, fontsize=11)

            ax.set_title("Renewable surplus absorbed compared to generation-only")
            ax.set_ylabel("Additional renewable surplus absorbed [GWh]")
            ax.set_xlabel("")
            _apply_axis_style(ax)
            ax.tick_params(axis="x", rotation=15)

            _save_figure(fig, output_path.parent / "relative_renewable_surplus_absorbed.png")

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

    df["plot_label"] = _strategy_labels(df["scenario"])
    colors = _strategy_colors(df["scenario"])

    fig, ax = plt.subplots(figsize=(10.5, 7), constrained_layout=True)

    ax.scatter(
        df[x_col] / 1e3,
        df[y_col] / 1e6,
        s=190,
        color=colors,
        alpha=0.8,
        edgecolor="black",
        linewidth=0.8,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["plot_label"],
            xy=(row[x_col] / 1e3, row[y_col] / 1e6),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=11,
        )

    ax.set_title("Storage-adjusted profit vs renewable surplus absorbed")
    ax.set_xlabel("Renewable surplus absorbed [GWh]")
    ax.set_ylabel("Profit [million EUR]")

    _apply_axis_style(ax)
    _save_figure(fig, output_path)


def save_pareto_frontier_plot(
    sweep_df: pd.DataFrame,
    output_path: Path,
):
    """
    Plot Pareto-optimal renewable-support strategies.

    Pareto-optimal means:
    no other point has BOTH
    - higher renewable surplus absorption
    - higher storage-adjusted profit
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = sweep_df.copy()

    if "error" in df.columns:
        df = df[df["error"].isna()]

    if df.empty:
        return

    x_col = "renewable_surplus_absorbed_MWh"

    if "adjusted_total_profit_EUR" in df.columns:
        y_col = "adjusted_total_profit_EUR"
    elif "storage_adjusted_profit_EUR" in df.columns:
        y_col = "storage_adjusted_profit_EUR"
    else:
        start_storage_MWh = 820040.0
        terminal_storage_price_EUR_per_MWh = 124.1725

        df["adjusted_total_profit_EUR"] = (
            df["total_profit_EUR"]
            + (df["final_storage_MWh"] - start_storage_MWh)
            * terminal_storage_price_EUR_per_MWh
        )
        y_col = "adjusted_total_profit_EUR"

    df = df.dropna(subset=[x_col, y_col])

    if df.empty:
        return

    # Convert to poster-friendly units
    df["x_GWh"] = df[x_col] / 1e3
    df["y_million_EUR"] = df[y_col] / 1e6

    # Pareto detection
    pareto_mask = []

    for i, row_i in df.iterrows():
        dominated = False

        for j, row_j in df.iterrows():
            if i == j:
                continue

            better_or_equal_x = row_j["x_GWh"] >= row_i["x_GWh"]
            better_or_equal_y = row_j["y_million_EUR"] >= row_i["y_million_EUR"]

            strictly_better = (
                row_j["x_GWh"] > row_i["x_GWh"]
                or row_j["y_million_EUR"] > row_i["y_million_EUR"]
            )

            if better_or_equal_x and better_or_equal_y and strictly_better:
                dominated = True
                break

        pareto_mask.append(not dominated)

    df["pareto_optimal"] = pareto_mask
    pareto_df = df[df["pareto_optimal"]].copy().sort_values("x_GWh")

    print("\nPareto-optimal strategies:")
    print(
        pareto_df[
            [
                "high_quantile",
                "safety_margin",
                "seasonal_strength",
                x_col,
                y_col,
            ]
        ]
    )

    fig, ax = plt.subplots(figsize=(12.5, 7.2), constrained_layout=True)

    # Dominated points
    ax.scatter(
        df.loc[~df["pareto_optimal"], "x_GWh"],
        df.loc[~df["pareto_optimal"], "y_million_EUR"],
        color=PLOT_COLORS["dominated"],
        s=75,
        alpha=0.32,
        label="Dominated strategies",
    )

    # Pareto points
    ax.scatter(
        pareto_df["x_GWh"],
        pareto_df["y_million_EUR"],
        color=PLOT_COLORS["pareto"],
        s=190,
        edgecolor="black",
        linewidth=1.1,
        label="Pareto-optimal strategies",
        zorder=3,
    )

    # Connect Pareto front
    ax.plot(
        pareto_df["x_GWh"],
        pareto_df["y_million_EUR"],
        color=PLOT_COLORS["pareto"],
        linewidth=3.0,
        alpha=0.85,
        zorder=2,
    )

    # Parameter labels
    for _, row in pareto_df.iterrows():
        label = (
            f"HQ={row['high_quantile']:.2f}\n"
            f"SM={row['safety_margin']:.2f}"
        )


        ax.annotate(
            label,
            xy=(row["x_GWh"], row["y_million_EUR"]),
            xytext=(7, 7),
            textcoords="offset points",
            fontsize=10,
        )

    # Explanation textbox for parameter abbreviations
    explanation_text = (
        "HQ = High quantile threshold\n"
        "SM = Safety margin"
    )

    ax.text(
            0.03,
            0.05,
            explanation_text,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment="bottom",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="white",
                edgecolor="gray",
                alpha=0.9,
            ),
    )

    ax.set_title("Trade-off between profit and renewable integration")

    ax.set_xlabel("Renewable surplus absorbed [GWh]")

    ax.set_ylabel("Profit [million EUR]")

    _apply_axis_style(ax)

    ax.legend(
        loc="upper right",
        frameon=False,
    )

    _save_figure(fig, output_path)


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

    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)

    values_gwh = monthly["renewable_surplus_absorbed_MWh"] / 1e3
    bars = ax.bar(
        monthly["month"],
        values_gwh,
        color="#2CA25F",
        edgecolor="black",
        linewidth=0.6,
    )
    if len(monthly) <= 12:
        ax.bar_label(bars, labels=[f"{value:.0f}" if value > 0 else "" for value in values_gwh], padding=3, fontsize=10)

    ax.set_title("Monthly renewable surplus absorbed")
    ax.set_ylabel("Renewable surplus absorbed [GWh]")
    ax.set_xlabel("Month")
    _apply_axis_style(ax)
    ax.tick_params(axis="x", rotation=30)

    _save_figure(fig, output_path)

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

    fig, ax = plt.subplots(figsize=(13, 6), constrained_layout=True)

    ax.plot(
        before_week["datetime"],
        before_week["deficit_before_MWh"],
        label="Deficit before storage",
        color=PLOT_COLORS["deficit"],
        linewidth=LINEWIDTH,
    )

    ax.plot(
        after_week["datetime"],
        after_week["deficit_after_MWh"],
        label="Deficit after storage",
        color=STRATEGY_COLORS["Renewable balanced"],
        linewidth=LINEWIDTH,
    )

    ax.fill_between(
        after_week["datetime"],
        after_week["deficit_after_MWh"],
        before_week["deficit_before_MWh"],
        where=before_week["deficit_before_MWh"] > after_week["deficit_after_MWh"],
        color=PLOT_COLORS["reduced"],
        alpha=0.28,
        label="Deficit reduced",
    )

    ax.set_title(
        f"Grid deficit before and after storage dispatch "
        f"({start:%Y-%m-%d} to {(end - timedelta(hours=1)):%Y-%m-%d})"
    )
    ax.set_ylabel("Deficit [MWh/h]")
    ax.set_xlabel("Time")
    _apply_axis_style(ax)
    ax.legend(frameon=False)

    fig.autofmt_xdate()
    _save_figure(fig, output_path)


def save_yearly_storage_poster_plot(
    scenario_results,
    output_path,
    storage_capacity_mwh,
    scenarios_to_plot=None,
    smoothing_hours=168,
):
    import matplotlib.pyplot as plt
    import pandas as pd

    if scenarios_to_plot is None:
        scenarios_to_plot = {
            "generation_only_rolling_24h": "Generation only",
            "rolling_24h_price_arbitrage_max": "Rolling 24h arbitrage",
            "renewable_support_balanced": "Renewable balanced",
        }

    colors = {
        "Generation only": "#7f7f7f",
        "Rolling 24h arbitrage": "#1f77b4",
        "Renewable balanced": "#2ca02c",
    }

    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)

    for scenario_key, label in scenarios_to_plot.items():
        if scenario_key not in scenario_results:
            print(f"Skipping missing scenario: {scenario_key}")
            continue

        df = scenario_results[scenario_key].copy()

        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            x = df["datetime"]
        else:
            x = df.index

        storage_percent = 100 * df["storage_MWh"] / storage_capacity_mwh

        if smoothing_hours is not None and smoothing_hours > 1:
            storage_percent = (
                storage_percent
                .rolling(window=smoothing_hours, min_periods=1, center=True)
                .mean()
            )

        ax.plot(
            x,
            storage_percent,
            label=label,
            linewidth=2.8,
            color=colors.get(label),
        )

    ax.set_title("Reservoir level throughout the year", fontsize=17, weight="bold")
    ax.set_ylabel("Reservoir filling level [%]", fontsize=14)
    ax.set_xlabel("Month", fontsize=14)

    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.25)

    ax.legend(
        fontsize=12,
        frameon=False,
        loc="best",
    )

    ax.tick_params(axis="both", labelsize=12)

    save_figure_with_vector_copy(fig, output_path, dpi=300)
    plt.close(fig)

    print(f"Saved yearly storage poster plot to {output_path}")
