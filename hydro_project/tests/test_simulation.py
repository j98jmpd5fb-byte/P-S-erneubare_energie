import pandas as pd

from src.plant import HydroPlant
from src.simulation import run_simulation
from src.strategy import rolling_24h_price_arbitrage_strategy


def make_test_plant():
    return HydroPlant(
        name="Test plant",
        storage_capacity_MWh=1000,
        turbine_power_MW=100,
        pump_power_MW=100,
        roundtrip_efficiency=0.8,
        initial_storage_MWh=500,
    )


def make_market_data(prices):
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=len(prices), freq="h"),
            "price_EUR_per_MWh": prices,
            "load_MW": [8000] * len(prices),
            "production_MW": [7500] * len(prices),
            "import_MW": [500] * len(prices),
            "export_MW": [0] * len(prices),
        }
    )


def test_storage_never_exceeds_capacity():
    plant = make_test_plant()
    for _ in range(20):
        plant.pump(plant.pump_power_MW, 1)
    assert plant.storage_MWh <= plant.storage_capacity_MWh


def test_storage_never_goes_below_zero():
    plant = make_test_plant()
    for _ in range(20):
        plant.generate(plant.turbine_power_MW, 1)
    assert plant.storage_MWh >= 0


def test_storage_respects_operating_bounds():
    plant = HydroPlant(
        name="Bounded plant",
        storage_capacity_MWh=1000,
        turbine_power_MW=100,
        pump_power_MW=100,
        roundtrip_efficiency=0.8,
        initial_storage_MWh=500,
        min_storage_fraction=0.1,
        max_storage_fraction=0.9,
    )

    for _ in range(20):
        plant.pump(plant.pump_power_MW, 1)
    assert plant.storage_MWh == 900

    for _ in range(20):
        plant.generate(plant.turbine_power_MW, 1)
    assert plant.storage_MWh == 100


def test_pumping_costs_money():
    plant = make_test_plant()
    results = run_simulation(make_market_data([10]), plant, 20, 80)
    assert results.loc[0, "action"] == "pump"
    assert results.loc[0, "cost_EUR"] > 0
    assert results.loc[0, "profit_EUR"] < 0


def test_generation_creates_revenue():
    plant = make_test_plant()
    results = run_simulation(make_market_data([100]), plant, 20, 80)
    assert results.loc[0, "action"] == "generate"
    assert results.loc[0, "revenue_EUR"] > 0
    assert results.loc[0, "profit_EUR"] > 0


def test_simulation_returns_expected_columns():
    plant = make_test_plant()
    results = run_simulation(make_market_data([10, 50, 100]), plant, 20, 80)
    expected_columns = [
        "datetime",
        "price_EUR_per_MWh",
        "load_MW",
        "production_MW",
        "import_MW",
        "export_MW",
        "net_balance_MW",
        "deficit_MW",
        "surplus_MW",
        "action",
        "pump_MWh",
        "generation_MWh",
        "storage_MWh",
        "cost_EUR",
        "revenue_EUR",
        "profit_EUR",
        "deficit_after_storage_MW",
        "surplus_after_storage_MW",
        "import_reduction_MWh",
        "surplus_absorbed_MWh",
        "low_threshold",
        "high_threshold",
        "scenario",
    ]
    assert list(results.columns) == expected_columns


def test_rolling_24h_strategy_records_thresholds():
    plant = make_test_plant()
    market_data = make_market_data([10, 20, 30, 40, 50, 60])
    results = run_simulation(
        market_data,
        plant,
        strategy=rolling_24h_price_arbitrage_strategy,
        strategy_kwargs={},
    )
    assert "low_threshold" in results.columns
    assert "high_threshold" in results.columns
    assert not results["low_threshold"].isna().all()
    assert not results["high_threshold"].isna().all()
