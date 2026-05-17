import numpy as np


def _window_thresholds(prices):
    prices = np.asarray(prices, dtype=float)
    if prices.size == 0:
        return None, None
    low_threshold = float(np.nanpercentile(prices, 25))
    high_threshold = float(np.nanpercentile(prices, 75))
    return low_threshold, high_threshold


def automatic_price_thresholds(prices):
    """Use simple global quartiles as a first automatic rule."""
    return _window_thresholds(prices)

def compute_grid_thresholds(market_data):
    """Compute data-dependent thresholds for Swiss grid strategies."""

    load = market_data["load_MW"].astype(float)
    production = market_data["production_MW"].astype(float)
    import_mw = market_data["import_MW"].astype(float)
    export_mw = market_data["export_MW"].astype(float)

    net_balance = production - load

    surplus = np.maximum(net_balance, 0.0)
    deficit = np.maximum(-net_balance, 0.0)

    surplus_positive = surplus[surplus > 0]
    deficit_positive = deficit[deficit > 0]

    return {
        "import_high_threshold": float(np.nanpercentile(import_mw, 75)),
        "export_high_threshold": float(np.nanpercentile(export_mw, 75)),
        "surplus_high_threshold": float(np.nanpercentile(surplus_positive, 75)) if len(surplus_positive) > 0 else 0.0,
        "deficit_high_threshold": float(np.nanpercentile(deficit_positive, 75)) if len(deficit_positive) > 0 else 0.0,
    }


def threshold_strategy(price, low_price_threshold, high_price_threshold):
    if price < low_price_threshold:
        return "pump"
    if price > high_price_threshold:
        return "generate"
    return "idle"


def price_arbitrage_strategy(current_row, future_window=None, global_low=None, global_high=None, **kwargs):
    if global_low is None or global_high is None:
        raise ValueError("Global price arbitrage requires global_low and global_high thresholds.")
    action = threshold_strategy(
        float(current_row["price_EUR_per_MWh"]),
        global_low,
        global_high,
    )
    return {
        "action": action,
        "low_threshold": global_low,
        "high_threshold": global_high,
    }

def generation_only_rolling_24h_strategy(current_row, future_window=None, **kwargs):
    """Hydropower without pumping: generate during high-price hours or when storage is nearly full."""

    prices = future_window["price_EUR_per_MWh"] if future_window is not None else []
    _, high_threshold = _window_thresholds(prices)

    if high_threshold is None:
        price = float(current_row["price_EUR_per_MWh"])
        high_threshold = price

    current_price = float(current_row["price_EUR_per_MWh"])
    storage_fraction = float(current_row.get("storage_fraction", 0.5))

    very_high_storage_fraction = kwargs.get("very_high_storage_fraction", 0.95)

    if current_price >= high_threshold:
        action = "generate"
    elif storage_fraction >= very_high_storage_fraction:
        action = "generate"
    else:
        action = "idle"

    return {
        "action": action,
        "low_threshold": np.nan,
        "high_threshold": high_threshold,
    }


def rolling_24h_price_arbitrage_strategy(current_row, future_window=None, **kwargs):
    prices = future_window["price_EUR_per_MWh"] if future_window is not None else []
    low_threshold, high_threshold = _window_thresholds(prices)
    if low_threshold is None or high_threshold is None:
        price = float(current_row["price_EUR_per_MWh"])
        low_threshold = high_threshold = price
    action = threshold_strategy(
        float(current_row["price_EUR_per_MWh"]),
        low_threshold,
        high_threshold,
    )

    storage_fraction = float(current_row.get("storage_fraction", 0.5))

    if action == "pump" and storage_fraction > 0.90:
        action = "idle"

    if storage_fraction > 0.97 and action != "pump":
        action = "generate"

    return {
        "action": action,
        "low_threshold": low_threshold,
        "high_threshold": high_threshold,
    }


def import_reduction_strategy(current_row, future_window=None, **kwargs):
    """Generate during high-import deficit hours; pump during high-export surplus hours."""

    load = float(current_row.get("load_MW", 0.0))
    production = float(current_row.get("production_MW", 0.0))
    import_mw = float(current_row.get("import_MW", 0.0))
    export_mw = float(current_row.get("export_MW", 0.0))

    import_threshold = kwargs.get("import_high_threshold", np.inf)
    export_threshold = kwargs.get("export_high_threshold", np.inf)

    net_balance = production - load

    if import_mw >= import_threshold:
        return {
            "action": "generate",
            "low_threshold": np.nan,
            "high_threshold": import_threshold,
        }

    if export_mw >= export_threshold:
        return {
            "action": "pump",
            "low_threshold": export_threshold,
            "high_threshold": np.nan,
        }

    return {
        "action": "idle",
        "low_threshold": np.nan,
        "high_threshold": np.nan,
    }


def surplus_absorption_strategy(current_row, future_window=None, **kwargs):
    """Pump during high-surplus hours; generate during high-deficit hours."""

    load = float(current_row.get("load_MW", 0.0))
    production = float(current_row.get("production_MW", 0.0))

    surplus_threshold = kwargs.get("surplus_high_threshold", np.inf)
    deficit_threshold = kwargs.get("deficit_high_threshold", np.inf)

    net_balance = production - load
    surplus = max(net_balance, 0.0)
    deficit = max(-net_balance, 0.0)

    if surplus >= surplus_threshold:
        return {
            "action": "pump",
            "low_threshold": surplus_threshold,
            "high_threshold": np.nan,
        }

    if deficit >= deficit_threshold:
        return {
            "action": "generate",
            "low_threshold": np.nan,
            "high_threshold": deficit_threshold,
        }

    return {
        "action": "idle",
        "low_threshold": np.nan,
        "high_threshold": np.nan,
    }


def renewable_balancing_strategy(current_row, future_window=None, **kwargs):
    """Use storage to smooth strong surplus/deficit situations."""

    load = float(current_row.get("load_MW", 0.0))
    production = float(current_row.get("production_MW", 0.0))
    import_mw = float(current_row.get("import_MW", 0.0))
    export_mw = float(current_row.get("export_MW", 0.0))

    surplus_threshold = kwargs.get("surplus_high_threshold", np.inf)
    deficit_threshold = kwargs.get("deficit_high_threshold", np.inf)
    import_threshold = kwargs.get("import_high_threshold", np.inf)
    export_threshold = kwargs.get("export_high_threshold", np.inf)

    net_balance = production - load
    surplus = max(net_balance, 0.0)
    deficit = max(-net_balance, 0.0)

    if surplus >= surplus_threshold or export_mw >= export_threshold:
        return {
            "action": "pump",
            "low_threshold": surplus_threshold,
            "high_threshold": np.nan,
        }

    if deficit >= deficit_threshold or import_mw >= import_threshold:
        return {
            "action": "generate",
            "low_threshold": np.nan,
            "high_threshold": deficit_threshold,
        }

    return {
        "action": "idle",
        "low_threshold": np.nan,
        "high_threshold": np.nan,
    }


SCENARIO_STRATEGIES = {
    "price_arbitrage_global": price_arbitrage_strategy,
    "generation_only_rolling_24h": generation_only_rolling_24h_strategy,
    "rolling_24h_price_arbitrage": rolling_24h_price_arbitrage_strategy,
    "import_reduction": import_reduction_strategy,
    "surplus_absorption": surplus_absorption_strategy,
    "renewable_balancing": renewable_balancing_strategy,
}
