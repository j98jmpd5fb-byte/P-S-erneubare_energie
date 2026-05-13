import pandas as pd

from src.strategy import threshold_strategy


def run_simulation(
    market_data,
    plant,
    low_price_threshold=None,
    high_price_threshold=None,
    action_column=None,
):
    """Run a transparent hourly pumped-storage simulation.

    Pumped storage is treated like a battery: it buys electricity, stores less
    useful energy than it bought because round-trip efficiency is below 1, and
    later sells electricity by drawing down the stored energy.
    """
    hourly_results = []
    duration_h = 1.0

    for _, row in market_data.iterrows():
        price = row["price_EUR_per_MWh"]
        if action_column:
            action = row[action_column]
        else:
            action = threshold_strategy(price, low_price_threshold, high_price_threshold)

        pump_MWh = 0.0
        generation_MWh = 0.0

        if action == "pump":
            pump_MWh = plant.pump(plant.pump_power_MW, duration_h)
            if pump_MWh == 0:
                action = "idle"
        elif action == "generate":
            generation_MWh = plant.generate(plant.turbine_power_MW, duration_h)
            if generation_MWh == 0:
                action = "idle"

        cost_EUR = pump_MWh * price
        revenue_EUR = generation_MWh * price
        profit_EUR = revenue_EUR - cost_EUR

        hourly_results.append(
            {
                "datetime": row["datetime"],
                "price_EUR_per_MWh": price,
                "action": action,
                "pump_MWh": pump_MWh,
                "generation_MWh": generation_MWh,
                "storage_MWh": plant.storage_MWh,
                "cost_EUR": cost_EUR,
                "revenue_EUR": revenue_EUR,
                "profit_EUR": profit_EUR,
                "import_MW": row["import_MW"],
                "load_MW": row["load_MW"],
            }
        )

    return pd.DataFrame(hourly_results)
