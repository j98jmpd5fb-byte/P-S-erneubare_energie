from pathlib import Path
import shutil

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.plots import save_all_plots
from src.simulation import run_dispatch_strategy
from src.strategy import automatic_price_thresholds


strategy = "seasonal_day_ahead"

cheap_percentile = 25
expensive_percentile = 75
min_reservoir_low_value_month = 0.05
min_reservoir_high_value_month = 0.85
top_price_fraction_for_water_value = 0.20
minimum_daily_spread_EUR_per_MWh = 0.0
target_reservoir_buffer_fraction = 0.0
seasonal_generation_premium_fraction = 0.0
reserve_release_percentile = 100
seasonal_refill_pump_percentile = 30


def save_run_bundle(data_dir, output_dir, run_dir):
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"

    if run_dir.exists():
        shutil.rmtree(run_dir)

    inputs_dir.mkdir(parents=True)
    outputs_dir.mkdir(parents=True)

    for input_file in data_dir.iterdir():
        if input_file.is_file():
            shutil.copy2(input_file, inputs_dir / input_file.name)

    for output_file in output_dir.iterdir():
        if output_file.is_file():
            shutil.copy2(output_file, outputs_dir / output_file.name)


def main():
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    run_dir = project_dir / "simulation_run"
    output_dir.mkdir(exist_ok=True)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")
    market_data = load_market_data(data_dir / "hourly_market_data_sample.csv")

    low_threshold, high_threshold = automatic_price_thresholds(
        market_data["price_EUR_per_MWh"]
    )

    # Replace this with a separate previous-year CSV when one is available.
    # The seasonal strategy uses it only for monthly statistics, not hourly
    # current-year foresight.
    previous_year_market_data = market_data

    strategy_kwargs = {}
    if strategy == "perfect_foresight":
        strategy_kwargs = {
            "low_price_threshold": low_threshold,
            "high_price_threshold": high_threshold,
        }
    elif strategy == "day_ahead":
        strategy_kwargs = {
            "cheap_percentile": cheap_percentile,
            "expensive_percentile": expensive_percentile,
        }
    elif strategy == "seasonal_day_ahead":
        strategy_kwargs = {
            "previous_year_market_data": previous_year_market_data,
            "cheap_percentile": cheap_percentile,
            "expensive_percentile": expensive_percentile,
            "min_reservoir_low_value_month": min_reservoir_low_value_month,
            "min_reservoir_high_value_month": min_reservoir_high_value_month,
            "top_price_fraction_for_water_value": top_price_fraction_for_water_value,
            "minimum_daily_spread_EUR_per_MWh": minimum_daily_spread_EUR_per_MWh,
            "target_reservoir_buffer_fraction": target_reservoir_buffer_fraction,
            "seasonal_generation_premium_fraction": seasonal_generation_premium_fraction,
            "reserve_release_percentile": reserve_release_percentile,
            "seasonal_refill_pump_percentile": seasonal_refill_pump_percentile,
        }

    print(f"Using dispatch strategy: {strategy}")
    results = run_dispatch_strategy(
        strategy=strategy,
        market_data=market_data,
        plant=plant,
        **strategy_kwargs,
    )

    metrics = calculate_metrics(results)
    results.to_csv(output_dir / "simulation_results.csv", index=False)
    save_all_plots(results, output_dir)
    save_run_bundle(data_dir, output_dir, run_dir)

    print(f"Plant: {plant.name}")
    if strategy == "perfect_foresight":
        print(f"Low price threshold: {low_threshold:.2f} EUR/MWh")
        print(f"High price threshold: {high_threshold:.2f} EUR/MWh")
    else:
        print(f"Cheap daily percentile: {cheap_percentile}")
        print(f"Expensive daily percentile: {expensive_percentile}")
    print("\nSummary metrics")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")
    print(f"\nSaved input/output bundle to: {run_dir}")


if __name__ == "__main__":
    main()
