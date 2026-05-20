import pandas as pd

from src.plant import HydroPlant
from src.simulation import run_dispatch_strategy, run_simulation


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
        "action",
        "pump_MWh",
        "generation_MWh",
        "storage_MWh",
        "cost_EUR",
        "revenue_EUR",
        "profit_EUR",
        "import_MW",
        "load_MW",
    ]
    assert list(results.columns) == expected_columns


def test_dispatcher_rejects_invalid_strategy():
    plant = make_test_plant()
    try:
        run_dispatch_strategy("not_a_strategy", make_market_data([10]), plant)
    except ValueError as error:
        assert "Allowed values" in str(error)
    else:
        raise AssertionError("Invalid strategy should raise ValueError.")


def test_seasonal_day_ahead_can_release_seasonal_reserve_for_strong_peaks():
    plant = HydroPlant(
        name="Seasonal plant",
        storage_capacity_MWh=1000,
        turbine_power_MW=100,
        pump_power_MW=100,
        roundtrip_efficiency=0.8,
        initial_storage_MWh=700,
    )
    market_data = make_market_data([10, 20, 30, 40, 100, 110, 120, 130])
    historical_data = market_data.copy()

    results = run_dispatch_strategy(
        "seasonal_day_ahead",
        market_data,
        plant,
        previous_year_market_data=historical_data,
        cheap_percentile=25,
        expensive_percentile=75,
        min_reservoir_low_value_month=0.60,
        min_reservoir_high_value_month=0.60,
        top_price_fraction_for_water_value=0.20,
    )

    assert results["storage_MWh"].min() >= plant.min_storage_MWh
    assert results["generation_MWh"].sum() > 0
