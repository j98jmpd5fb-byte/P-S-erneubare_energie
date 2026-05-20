import numpy as np


def automatic_price_thresholds(prices):
    """Use simple quartiles as a first automatic rule."""
    low_threshold = np.percentile(prices, 25)
    high_threshold = np.percentile(prices, 75)
    return float(low_threshold), float(high_threshold)


def threshold_strategy(price, low_price_threshold, high_price_threshold):
    if price < low_price_threshold:
        return "pump"
    if price > high_price_threshold:
        return "generate"
    return "idle"


def percentile_thresholds(prices, cheap_percentile=25, expensive_percentile=75):
    """Return low/high percentile thresholds for a local price window."""
    cheap_threshold = np.percentile(prices, cheap_percentile)
    expensive_threshold = np.percentile(prices, expensive_percentile)
    return float(cheap_threshold), float(expensive_threshold)


def normalize_monthly_values(monthly_values):
    """Normalize monthly water values to the range 0..1."""
    min_value = min(monthly_values.values())
    max_value = max(monthly_values.values())

    if np.isclose(min_value, max_value):
        return {month: 0.5 for month in monthly_values}

    return {
        month: (value - min_value) / (max_value - min_value)
        for month, value in monthly_values.items()
    }


def calculate_monthly_water_values(
    market_data,
    top_price_fraction_for_water_value=0.20,
):
    """Estimate monthly water values from historical monthly price peaks.

    The returned values are monthly statistics only. They are suitable for a
    seasonal prior, but they should not be interpreted as hourly current-year
    foresight.
    """
    if not 0 < top_price_fraction_for_water_value <= 1:
        raise ValueError("top_price_fraction_for_water_value must be in (0, 1].")

    historical_data = market_data.copy()
    historical_data["month"] = historical_data["datetime"].dt.month
    monthly_values = {}

    for month, month_data in historical_data.groupby("month"):
        prices = month_data["price_EUR_per_MWh"].sort_values(ascending=False)
        top_count = max(
            1,
            int(np.ceil(len(prices) * top_price_fraction_for_water_value)),
        )
        monthly_values[int(month)] = float(prices.head(top_count).mean())

    if not monthly_values:
        raise ValueError("Cannot calculate monthly water values from empty data.")

    return monthly_values
