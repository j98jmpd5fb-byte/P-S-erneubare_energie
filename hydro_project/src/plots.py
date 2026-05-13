import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("/private/tmp/hydro_project_mpl")))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def save_all_plots(results, output_dir):
    output_dir.mkdir(exist_ok=True)
    _plot_price(results, output_dir)
    _plot_storage(results, output_dir)
    _plot_actions(results, output_dir)
    _plot_cumulative_profit(results, output_dir)


def _plot_price(results, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(results["datetime"], results["price_EUR_per_MWh"], color="tab:blue")
    ax.set_title("Hourly electricity price")
    ax.set_ylabel("EUR/MWh")
    ax.set_xlabel("Time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "price_over_time.png", dpi=150)
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


def _plot_actions(results, output_dir):
    action_to_value = {"pump": -1, "idle": 0, "generate": 1}
    action_values = results["action"].map(action_to_value)

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.step(results["datetime"], action_values, where="mid", color="tab:purple")
    ax.set_title("Hourly operation action")
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
