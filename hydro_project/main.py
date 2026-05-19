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
    save_core_kpi_bar_plots,
    save_profit_vs_renewable_absorption_plot,
    save_deficit_vs_renewable_absorption_plot,
    save_adjusted_profit_plot,
    save_relative_improvement_plot,
    save_storage_adjusted_profit_vs_renewable_absorption_plot,
    save_monthly_renewable_surplus_absorbed_plot,
    save_deficit_before_after_week_plot,
)
from src.simulation import run_simulation
from src.strategy import SCENARIO_STRATEGIES, automatic_price_thresholds
from itertools import product

def main(dataset="simulation_input_2025.csv"):
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    core_dir = output_dir / "core_plots"
    operational_dir = output_dir / "operational_plots"
    csv_dir = output_dir / "csv"

    core_dir.mkdir(parents=True, exist_ok=True)
    operational_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")
    market_data = load_market_data(data_dir / dataset)

    market_data = load_market_data(data_dir / dataset)

    market_data["grid_surplus_MWh"] = (
        market_data["total_production_MWh"]
        - market_data["total_consumption_MWh"]
    ).clip(lower=0)

    market_data["renewable_fraction"] = (
        market_data["renewable_MW"]
        / market_data["total_production_MW_avg"].replace(0, pd.NA)
    ).fillna(0)


    # ============================================================
    # Renewable and Surplus Checks
    # ============================================================

    # print("\nSurplus diagnostics")
    # print("Hours with grid surplus:", (market_data["grid_surplus_MWh"] > 0).sum())
    # print("Max grid surplus:", market_data["grid_surplus_MWh"].max())
    # print("Mean grid surplus:", market_data["grid_surplus_MWh"].mean())

    # print("\nRenewable fraction diagnostics")
    # print(market_data["renewable_fraction"].describe())

    # condition = (
    #     (market_data["grid_surplus_MWh"] > 0)
    #     & (market_data["renewable_fraction"] >= 0.5)
    # )

    # print("\nHybrid strategy trigger diagnostics")
    # print("Hours satisfying surplus + renewable condition:", condition.sum())
    # print("Share of year:", condition.mean())

    # ============================================================
    # For the other strategies that are not computed
    # ============================================================

    # grid_thresholds = compute_grid_thresholds(market_data)
    # global_low, global_high = automatic_price_thresholds(
    #     market_data["price_EUR_per_MWh"]
    # )

    # ============================================================
    # Various Parameters for rolling_max
    # ============================================================

    # low_quantiles = [0.15, 0.20, 0.25, 0.30]
    # high_quantiles = [0.70, 0.75, 0.80, 0.85]
    # safety_margins = [1.00, 1.05, 1.10, 1.15]

    # rolling_parameter_sets = []

    # for low_q, high_q, margin in product(
    #     low_quantiles,
    #     high_quantiles,
    #     safety_margins,
    # ):
    #     if low_q >= high_q:
    #         continue

    #     rolling_parameter_sets.append({
    #         "name": f"rolling_profit_q{int(low_q * 100)}_q{int(high_q * 100)}_m{int(margin * 100)}",
    #         "title": f"Rolling profit q{low_q:.2f}/q{high_q:.2f}, margin {margin:.2f}",
    #         "kwargs": {
    #             "low_quantile": low_q,
    #             "high_quantile": high_q,
    #             "round_trip_efficiency": 0.8,
    #             "safety_margin": margin,
    #         },
    #     })

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
            "title": "Generation only",
            "strategy": SCENARIO_STRATEGIES["generation_only_rolling_24h"],
            "strategy_kwargs": {},
        },
        "rolling_24h_price_arbitrage_max": {
            "title": "Arbitrage",
            "strategy": SCENARIO_STRATEGIES["rolling_24h_price_arbitrage"],
            "strategy_kwargs": {
                "low_quantile": 0.30,
                "high_quantile": 0.85,
                "round_trip_efficiency": 0.75,
                "safety_margin": 1.15,
            },
        },
        "renewable_support_conservative": {
            "title": "Renew. conservative",
            "strategy": SCENARIO_STRATEGIES["renewable_surplus_plus_rolling_price"],
            "strategy_kwargs": {
                "min_surplus_mwh": 0.0,
                "min_renewable_fraction": 0.5,
                "low_quantile": 0.20,
                "high_quantile": 0.70,
                "round_trip_efficiency": 0.75,
                "safety_margin": 1.00,
            },
        },
        "renewable_support_balanced": {
            "title": "Renew. balanced",
            "strategy": SCENARIO_STRATEGIES["renewable_surplus_plus_rolling_price"],
            "strategy_kwargs": {
                "min_surplus_mwh": 0.0,
                "min_renewable_fraction": 0.4,
                "low_quantile": 0.20,
                "high_quantile": 0.80,
                "round_trip_efficiency": 0.75,
                "safety_margin": 0.95,
            },
        },
        "renewable_support_aggressive": {
            "title": "Renew. aggressive",
            "strategy": SCENARIO_STRATEGIES["renewable_surplus_plus_rolling_price"],
            "strategy_kwargs": {
                "min_surplus_mwh": 0.0,
                "min_renewable_fraction": 0.3,
                "low_quantile": 0.20,
                "high_quantile": 0.85,
                "round_trip_efficiency": 0.75,
                "safety_margin": 0.90,
            },
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

    # ============================================================
    # Looping through various parameters
    # ============================================================

    # for param_set in rolling_parameter_sets:
    #     scenario_definitions[param_set["name"]] = {
    #         "title": param_set["title"],
    #         "strategy": SCENARIO_STRATEGIES["rolling_24h_price_arbitrage"],
    #         "strategy_kwargs": param_set["kwargs"],
    #     }

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

        print(f"\nResult columns for {scenario_name}:")

        scenario_results[scenario_name] = results
        metrics = calculate_metrics(results, plant=plant_for_scenario)
        metrics["scenario"] = scenario_name
        metrics["strategy"] = scenario["title"]
        summary_rows.append(metrics)

        print(f"Summary for {scenario_name} ({scenario['title']}):")
        print(
            pd.DataFrame([{
                "total_profit_EUR": metrics["total_profit_EUR"],
                "terminal_storage_value_EUR": metrics["terminal_storage_value_EUR"],
                "adjusted_total_profit_EUR": metrics["adjusted_total_profit_EUR"],
                "final_storage_MWh": metrics["final_storage_MWh"],
            }]).to_string(index=False, float_format="{:.2f}".format)
        )

        results.to_csv(scenario_dir / "simulation_results.csv", index=False)
        save_all_plots(results, operational_dir / scenario_name)

    metrics_summary = pd.DataFrame(summary_rows)

    # ============================================================
    # Finding best economical scenario
    # ============================================================

    # rolling_results = metrics_summary[
    #     metrics_summary["scenario"].str.startswith("rolling_profit")
    # ]

    # best_rolling = rolling_results.sort_values(
    #     "total_profit_EUR",
    #     ascending=False
    # ).iloc[0]

    # print("\nBest rolling-profit strategy:")
    # print(best_rolling[[
    #     "scenario",
    #     "strategy",
    #     "total_profit_EUR",
    #     "total_pumped_MWh",
    #     "total_generated_MWh",
    #     "surplus_absorbed_MWh",
    #     "deficit_reduction_MWh",
    # ]])


    metrics_summary.to_csv(csv_dir / "metrics_summary.csv", index=False)
    save_scenario_comparison_plot(metrics_summary, core_dir)
    volatile_week = find_most_volatile_week(
        scenario_results["generation_only_rolling_24h"]
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
            pumped_storage_results=scenario_results["rolling_24h_price_arbitrage_max"],
            output_dir=operational_dir / "week_comparisons",
            start_date=start_date,
        )
        save_deficit_before_after_week_plot(
            scenario_results["generation_only_rolling_24h"],
            scenario_results["renewable_support_balanced"],
            Path("outputs")
            / "operational_plots"
            / "deficit_before_after"
            / f"deficit_before_after_balanced_{start_date}.png",
            start_date=start_date,
        )

    save_core_kpi_bar_plots(
        metrics_summary,
        core_dir,
    )

    save_profit_vs_renewable_absorption_plot(
        metrics_summary,
        core_dir / "profit_vs_renewable_absorption.png",
    )

    save_deficit_vs_renewable_absorption_plot(
        metrics_summary,
        core_dir / "deficit_vs_renewable_absorption.png",
    )

    save_adjusted_profit_plot(metrics_summary, core_dir)

    save_relative_improvement_plot(
        metrics_summary,
        Path("outputs") / "core_plots" / "relative_improvement_vs_generation_only.png",
    )

    save_storage_adjusted_profit_vs_renewable_absorption_plot(
        metrics_summary,
        Path("outputs") / "core_plots" / "storage_adjusted_profit_vs_renewable_absorption.png",
    )

    save_monthly_renewable_surplus_absorbed_plot(
        scenario_results["renewable_support_balanced"],
        Path("outputs") / "operational_plots" / "monthly_renewable_surplus_absorbed_balanced.png",
    )


    print(f"Plant: {plant.name}")
    print("\nScenario comparison summary")
    display_columns = [
        "scenario",
        "strategy",
        "total_profit_EUR",
        "terminal_storage_value_EUR",
        "adjusted_total_profit_EUR",
        "total_pumped_MWh",
        "total_generated_MWh",
        "deficit_reduction_MWh",
        "surplus_absorbed_MWh",
        "renewable_surplus_absorbed_MWh",
        "start_storage_MWh",
        "final_storage_MWh",
    ]
    print(metrics_summary[display_columns].to_string(index=False, float_format="{:.2f}".format))


if __name__ == "__main__":
    main()
