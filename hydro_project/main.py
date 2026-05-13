from pathlib import Path

from src.data_loader import load_market_data, load_plant_parameters
from src.metrics import calculate_metrics
from src.plots import save_all_plots
from src.simulation import run_simulation
from src.strategy import automatic_price_thresholds


def main():
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    plant = load_plant_parameters(data_dir / "plant_parameters.csv")
    market_data = load_market_data(data_dir / "hourly_market_data_sample.csv")

    low_threshold, high_threshold = automatic_price_thresholds(
        market_data["price_EUR_per_MWh"]
    )
    results = run_simulation(
        market_data=market_data,
        plant=plant,
        low_price_threshold=low_threshold,
        high_price_threshold=high_threshold,
    )

    metrics = calculate_metrics(results)
    results.to_csv(output_dir / "simulation_results.csv", index=False)
    save_all_plots(results, output_dir)

    print(f"Plant: {plant.name}")
    print(f"Low price threshold: {low_threshold:.2f} EUR/MWh")
    print(f"High price threshold: {high_threshold:.2f} EUR/MWh")
    print("\nSummary metrics")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
