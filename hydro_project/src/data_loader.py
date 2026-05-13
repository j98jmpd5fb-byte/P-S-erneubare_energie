import pandas as pd

from src.plant import HydroPlant


PLANT_COLUMNS = [
    "plant_name",
    "storage_capacity_MWh",
    "turbine_power_MW",
    "pump_power_MW",
    "roundtrip_efficiency",
    "initial_storage_MWh",
]

MARKET_COLUMNS = [
    "datetime",
    "price_EUR_per_MWh",
    "load_MW",
    "production_MW",
    "import_MW",
    "export_MW",
]


def load_plant_parameters(path):
    data = pd.read_csv(path)
    _check_columns(data, PLANT_COLUMNS, path)
    row = data.iloc[0]

    return HydroPlant(
        name=row["plant_name"],
        storage_capacity_MWh=row["storage_capacity_MWh"],
        turbine_power_MW=row["turbine_power_MW"],
        pump_power_MW=row["pump_power_MW"],
        roundtrip_efficiency=row["roundtrip_efficiency"],
        initial_storage_MWh=row["initial_storage_MWh"],
        min_storage_fraction=row.get("min_storage_fraction", 0.0),
        max_storage_fraction=row.get("max_storage_fraction", 1.0),
    )


def load_market_data(path):
    data = pd.read_csv(path)
    _check_columns(data, MARKET_COLUMNS, path)
    data["datetime"] = pd.to_datetime(data["datetime"])
    return data.sort_values("datetime").reset_index(drop=True)


def _check_columns(data, required_columns, path):
    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
