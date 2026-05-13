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


def build_day_ahead_schedule(
    market_data,
    pump_hours_per_day=6,
    generation_hours_per_day=6,
    roundtrip_efficiency=1.0,
):
    """Schedule daily actions from known day-ahead hourly prices.

    For each calendar day, pair cheap pumping hours with expensive generation
    hours. A pair is scheduled only when the spread covers round-trip losses.
    """
    scheduled = market_data.copy()
    scheduled["scheduled_action"] = "idle"

    for _, day_data in scheduled.groupby(scheduled["datetime"].dt.date):
        pump_count = min(pump_hours_per_day, len(day_data))
        pump_candidates = day_data.nsmallest(
            pump_count,
            "price_EUR_per_MWh",
        )

        remaining = day_data.drop(index=pump_candidates.index)
        generation_count = min(generation_hours_per_day, len(remaining))
        generation_candidates = remaining.nlargest(
            generation_count,
            "price_EUR_per_MWh",
        )

        for (_, pump_row), (_, generation_row) in zip(
            pump_candidates.iterrows(),
            generation_candidates.iterrows(),
        ):
            pump_price = pump_row["price_EUR_per_MWh"]
            generation_price = generation_row["price_EUR_per_MWh"]
            if generation_price * roundtrip_efficiency <= pump_price:
                continue

            scheduled.loc[pump_row.name, "scheduled_action"] = "pump"
            scheduled.loc[generation_row.name, "scheduled_action"] = "generate"

    return scheduled
