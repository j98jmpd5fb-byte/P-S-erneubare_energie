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

MARKET_REQUIRED_COLUMNS = ["datetime", "price_EUR_per_MWh"]

MONTHLY_INFLOW_MWH = {
    1: 40,
    2: 35,
    3: 50,
    4: 90,
    5: 160,
    6: 220,
    7: 200,
    8: 160,
    9: 110,
    10: 80,
    11: 60,
    12: 45,
}

MARKET_OPTIONAL_COLUMNS = [
    "load_MW",
    "production_MW",
    "import_MW",
    "export_MW",
    "natural_inflow_MWh",
]


def load_plant_parameters(path):
    data = pd.read_csv(path)

    rename_map = {
        "total_import_MW_avg": "import_MW",
        "total_export_MW_avg": "export_MW",
        "total_production_MW_avg": "production_MW",
        "total_consumption_MW_avg": "load_MW",
    }

    data = data.rename(columns=rename_map)

    _check_columns(data, PLANT_COLUMNS, path)
    row = data.iloc[0]

    def _optional_float(key, default=None):
        if key not in data.columns:
            return default
        value = row[key]
        return None if pd.isna(value) else float(value)

    return HydroPlant(
        name=row["plant_name"],
        storage_capacity_MWh=float(row["storage_capacity_MWh"]),
        turbine_power_MW=float(row["turbine_power_MW"]),
        pump_power_MW=float(row["pump_power_MW"]),
        roundtrip_efficiency=float(row["roundtrip_efficiency"]),
        initial_storage_MWh=float(row["initial_storage_MWh"]),
        pump_efficiency=_optional_float("pump_efficiency"),
        turbine_efficiency=_optional_float("turbine_efficiency") or 1.0,
        min_storage_fraction=_optional_float("min_storage_fraction", 0.0),
        max_storage_fraction=_optional_float("max_storage_fraction", 1.0),
        head_m=_optional_float("head_m"),
        usable_volume_m3=_optional_float("usable_volume_m3"),
    )


def load_market_data(path):
    data = pd.read_csv(path)
    # Preserve original aggregated column names (e.g. total_production_MW_avg)
    # but also create short convenience columns expected by the simulator
    mapping = {
        "total_import_MW_avg": "import_MW",
        "total_export_MW_avg": "export_MW",
        "total_production_MW_avg": "production_MW",
        "total_consumption_MW_avg": "load_MW",
    }

    for old_col, new_col in mapping.items():
        if old_col in data.columns and new_col not in data.columns:
            data[new_col] = pd.to_numeric(data[old_col], errors="coerce").fillna(0.0)

    _check_columns(data, MARKET_REQUIRED_COLUMNS, path)
    for column in MARKET_OPTIONAL_COLUMNS:
        if column not in data.columns:
            data[column] = 0.0
        else:
            data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

    data["datetime"] = pd.to_datetime(data["datetime"], errors="coerce")
    if data["datetime"].isna().any():
        raise ValueError(f"{path} contains invalid datetime values.")
    
    if "natural_inflow_MWh" not in data.columns or (data["natural_inflow_MWh"] == 0).all():
        data["natural_inflow_MWh"] = data["datetime"].dt.month.map(MONTHLY_INFLOW_MWH).fillna(0.0)

    return data.sort_values("datetime").reset_index(drop=True)


def _check_columns(data, required_columns, path):
    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
