from pathlib import Path

import pandas as pd

from src.data_loader import load_market_data, load_plant_parameters
from src.strategy import compute_grid_thresholds
from src.metrics import calculate_metrics
from src.plots import (
    save_all_plots,
    save_scenario_comparison_plot,
    save_strategy_week_comparison_plot,
    find_most_volatile_week,
)
from src.simulation import run_simulation
from src.strategy import SCENARIO_STRATEGIES, automatic_price_thresholds


def main(dataset="simulation_input_2025.csv"):
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")
    market_data = load_market_data(data_dir / dataset)
    # grid_thresholds = compute_grid_thresholds(market_data)

    global_low, global_high = automatic_price_thresholds(
        market_data["price_EUR_per_MWh"]
    )

    scenario_definitions = {
        # "price_arbitrage_global": {
        #     "title": "Global price arbitrage",
        #     "strategy": SCENARIO_STRATEGIES["price_arbitrage_global"],
        #     "strategy_kwargs": {
        #         "global_low": global_low,
        #         "global_high": global_high,
        #     },
        # },
        "generation_only_rolling_24h": {
            "title": "Current hydropower plant, no pumping",
            "strategy": SCENARIO_STRATEGIES["generation_only_rolling_24h"],
            "strategy_kwargs": {},
        },
        "rolling_24h_price_arbitrage": {
            "title": "Rolling 24h price arbitrage",
            "strategy": SCENARIO_STRATEGIES["rolling_24h_price_arbitrage"],
            "strategy_kwargs": {},
        },
        # "import_reduction": {
        #     "title": "Import reduction",
        #     "strategy": SCENARIO_STRATEGIES["import_reduction"],
        #     "strategy_kwargs": grid_thresholds,
        # },
        # "surplus_absorption": {
        #     "title": "Surplus absorption",
        #     "strategy": SCENARIO_STRATEGIES["surplus_absorption"],
        #     "strategy_kwargs": grid_thresholds,
        # },
        # "renewable_balancing": {
        #     "title": "Renewable balancing",
        #     "strategy": SCENARIO_STRATEGIES["renewable_balancing"],
        #     "strategy_kwargs": grid_thresholds,
        # },
    }

    summary_rows = []
    scenario_results = {}
    for scenario_name, scenario in scenario_definitions.items():
        scenario_dir = output_dir / scenario_name
        scenario_dir.mkdir(exist_ok=True)
        plant_for_scenario = load_plant_parameters(data_dir / "plant_parameters.csv")

        results = run_simulation(
            market_data=market_data,
            plant=plant_for_scenario,
            strategy=scenario["strategy"],
            strategy_kwargs=scenario["strategy_kwargs"],
            scenario=scenario_name,
        )

        # print(f"\nAction counts for {scenario_name}:")
        # print(results["action"].value_counts())
        scenario_results[scenario_name] = results
        metrics = calculate_metrics(results, plant=plant_for_scenario)
        metrics["scenario"] = scenario_name
        metrics["strategy"] = scenario["title"]
        summary_rows.append(metrics)

        results.to_csv(scenario_dir / "simulation_results.csv", index=False)
        save_all_plots(results, scenario_dir)

    metrics_summary = pd.DataFrame(summary_rows)
    metrics_summary.to_csv(output_dir / "metrics_summary.csv", index=False)
    save_scenario_comparison_plot(metrics_summary, output_dir)
    volatile_week = find_most_volatile_week(
        scenario_results["rolling_24h_price_arbitrage"]
    )

    comparison_weeks = [
        "2025-01-06",
        "2025-04-07",
        "2025-07-07",
        "2025-10-06",
    ]

    if volatile_week is not None and volatile_week not in comparison_weeks:
        comparison_weeks.append(volatile_week)

    for start_date in comparison_weeks:
        save_strategy_week_comparison_plot(
            generation_only_results=scenario_results["generation_only_rolling_24h"],
            pumped_storage_results=scenario_results["rolling_24h_price_arbitrage"],
            output_dir=output_dir,
            start_date=start_date,
        )

    print(f"Plant: {plant.name}")
    print("\nScenario comparison summary")
    display_columns = [
        "scenario",
        "strategy",
        "total_profit_EUR",
        "total_pumped_MWh",
        "total_generated_MWh",
        "deficit_reduction_MWh",
        "surplus_absorbed_MWh",
        "final_storage_MWh",
    ]
    print(metrics_summary[display_columns].to_string(index=False, float_format="{:.2f}".format))


if __name__ == "__main__":
    main()
