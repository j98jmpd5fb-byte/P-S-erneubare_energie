import pandas as pd
import numpy as np

from src.strategy import price_arbitrage_strategy


def _default_strategy(low_price_threshold, high_price_threshold):
    return lambda current_row, future_window=None, **kwargs: price_arbitrage_strategy(
        current_row,
        future_window=future_window,
        global_low=low_price_threshold,
        global_high=high_price_threshold,
    )


def run_simulation(
    market_data,
    plant,
    low_price_threshold=None,
    high_price_threshold=None,
    strategy=None,
    strategy_kwargs=None,
    scenario=None,
):
    """Run an hourly pumped-storage simulation with scenario-based dispatch."""
    if strategy is None:
        if low_price_threshold is None or high_price_threshold is None:
            raise ValueError(
                "run_simulation requires either a strategy or both low_price_threshold and high_price_threshold."
            )
        strategy = _default_strategy(low_price_threshold, high_price_threshold)

    strategy_kwargs = strategy_kwargs or {}
    market_data = market_data.copy()
    market_data["datetime"] = pd.to_datetime(market_data["datetime"], errors="coerce")
    market_data = market_data.sort_values("datetime").reset_index(drop=True)

    for column in ["load_MW", "production_MW", "import_MW", "export_MW"]:
        if column not in market_data.columns:
            market_data[column] = 0.0

    hourly_results = []
    duration_h = 1.0

    for index, row in market_data.iterrows():
        future_window = market_data.iloc[index : index + 25]
        row_for_strategy = row.copy()
        row_for_strategy["storage_MWh"] = plant.storage_MWh
        row_for_strategy["storage_fraction"] = plant.storage_MWh / plant.max_storage_MWh
        row_for_strategy["natural_inflow_MWh"] = float(row.get("natural_inflow_MWh", 0.0))
        decision = strategy(row_for_strategy, future_window=future_window, **strategy_kwargs)
        action = decision.get("action", "idle")
        low_threshold = decision.get("low_threshold", np.nan)
        high_threshold = decision.get("high_threshold", np.nan)

        current_price = float(row["price_EUR_per_MWh"])
        load_MW = float(row.get("load_MW", 0.0))
        production_MW = float(row.get("production_MW", 0.0))
        import_MW = float(row.get("import_MW", 0.0))
        export_MW = float(row.get("export_MW", 0.0))

        net_balance_MW = production_MW - load_MW
        deficit_MW = max(load_MW - production_MW, 0.0)
        surplus_MW = max(production_MW - load_MW, 0.0)

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

        cost_EUR = pump_MWh * current_price
        revenue_EUR = generation_MWh * current_price
        profit_EUR = revenue_EUR - cost_EUR

        deficit_after_storage_MW = max(deficit_MW - generation_MWh, 0.0)
        surplus_after_storage_MW = max(surplus_MW - pump_MWh, 0.0)
        import_reduction_MWh = min(generation_MWh, import_MW)
        surplus_absorbed_MWh = min(pump_MWh, export_MW)

        natural_inflow_MWh = float(row.get("natural_inflow_MWh", 0.0))
        stored_inflow_MWh, spilled_inflow_MWh = plant.add_inflow(natural_inflow_MWh)

        hourly_results.append(
            {
                "datetime": row["datetime"],
                "price_EUR_per_MWh": current_price,
                "load_MW": load_MW,
                "production_MW": production_MW,
                "import_MW": import_MW,
                "export_MW": export_MW,
                "net_balance_MW": net_balance_MW,
                "deficit_MW": deficit_MW,
                "surplus_MW": surplus_MW,
                "action": action,
                "pump_MWh": pump_MWh,
                "generation_MWh": generation_MWh,
                "storage_MWh": plant.storage_MWh,
                "cost_EUR": cost_EUR,
                "revenue_EUR": revenue_EUR,
                "profit_EUR": profit_EUR,
                "deficit_after_storage_MW": deficit_after_storage_MW,
                "surplus_after_storage_MW": surplus_after_storage_MW,
                "import_reduction_MWh": import_reduction_MWh,
                "surplus_absorbed_MWh": surplus_absorbed_MWh,
                "low_threshold": low_threshold,
                "high_threshold": high_threshold,
                "scenario": scenario,
                "natural_inflow_MWh": natural_inflow_MWh,
                "stored_inflow_MWh": stored_inflow_MWh,
                "spilled_inflow_MWh": spilled_inflow_MWh,
                "renewable_fraction": row.get("renewable_fraction", 0),
            }
        )

    return pd.DataFrame(hourly_results)
