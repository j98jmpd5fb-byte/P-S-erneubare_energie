from pathlib import Path

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.plots import save_all_plots
from src.simulation import run_simulation
from src.strategy import build_day_ahead_schedule


def main():
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")
    market_data = load_market_data(data_dir / "hourly_market_data_sample.csv")

    market_data = build_day_ahead_schedule(
        market_data,
        pump_hours_per_day=6,
        generation_hours_per_day=6,
        roundtrip_efficiency=plant.roundtrip_efficiency,
    )
    results = run_simulation(
        market_data=market_data,
        plant=plant,
        action_column="scheduled_action",
    )

    metrics = calculate_metrics(results)
    results.to_csv(output_dir / "simulation_results.csv", index=False)
    save_all_plots(results, output_dir)

    print(f"Plant: {plant.name}")
    print("Strategy: day-ahead schedule")
    print("Pump hours per day: 6")
    print("Generation hours per day: 6")
    print(f"Round-trip efficiency spread check: {plant.roundtrip_efficiency:.2f}")
    print("\nSummary metrics")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
