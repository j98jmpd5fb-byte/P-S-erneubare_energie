import pandas as pd

from src.strategy import (
    automatic_price_thresholds,
    calculate_monthly_water_values,
    normalize_monthly_values,
    percentile_thresholds,
    threshold_strategy,
)


ALLOWED_DISPATCH_STRATEGIES = (
    "perfect_foresight",
    "day_ahead",
    "seasonal_day_ahead",
)


def run_simulation(market_data, plant, low_price_threshold, high_price_threshold):
    """Backward-compatible wrapper for the original perfect-foresight logic."""
    return run_perfect_foresight_strategy(
        market_data=market_data,
        plant=plant,
        low_price_threshold=low_price_threshold,
        high_price_threshold=high_price_threshold,
    )


def run_dispatch_strategy(strategy, market_data, plant, **kwargs):
    """Run the selected dispatch strategy and return hourly simulation results."""
    if strategy == "perfect_foresight":
        return run_perfect_foresight_strategy(
            market_data=market_data,
            plant=plant,
            **kwargs,
        )
    if strategy == "day_ahead":
        return run_day_ahead_strategy(market_data=market_data, plant=plant, **kwargs)
    if strategy == "seasonal_day_ahead":
        return run_seasonal_day_ahead_strategy(
            market_data=market_data,
            plant=plant,
            **kwargs,
        )

    allowed = ", ".join(ALLOWED_DISPATCH_STRATEGIES)
    raise ValueError(
        f"Unknown dispatch strategy '{strategy}'. Allowed values: {allowed}."
    )


def run_perfect_foresight_strategy(
    market_data,
    plant,
    low_price_threshold=None,
    high_price_threshold=None,
):
    """Run a transparent hourly pumped-storage simulation.

    This is the original benchmark strategy. It calculates global price
    thresholds from the full simulated price series, so it has perfect
    knowledge of the whole horizon and should be treated as an upper bound.

    Pumped storage is treated like a battery: it buys electricity, stores less
    useful energy than it bought because round-trip efficiency is below 1, and
    later sells electricity by drawing down the stored energy.
    """
    hourly_results = []
    duration_h = 1.0

    if low_price_threshold is None or high_price_threshold is None:
        low_price_threshold, high_price_threshold = automatic_price_thresholds(
            market_data["price_EUR_per_MWh"]
        )

    for _, row in market_data.iterrows():
        price = row["price_EUR_per_MWh"]
        action = threshold_strategy(price, low_price_threshold, high_price_threshold)
        hourly_results.append(_simulate_hour(row, plant, action, duration_h))

    return pd.DataFrame(hourly_results)


def run_day_ahead_strategy(
    market_data,
    plant,
    cheap_percentile=25,
    expensive_percentile=75,
):
    """Dispatch with only same-day prices.

    Each calendar day is optimized myopically from that day's prices only:
    pump in cheap hours and generate in expensive hours, while the plant object
    enforces capacity, minimum storage, power limits, and round-trip losses.
    """
    hourly_results = []
    duration_h = 1.0

    for _, day_data in market_data.groupby(market_data["datetime"].dt.date, sort=True):
        cheap_threshold, expensive_threshold = percentile_thresholds(
            day_data["price_EUR_per_MWh"],
            cheap_percentile=cheap_percentile,
            expensive_percentile=expensive_percentile,
        )
        for _, row in day_data.iterrows():
            action = _daily_threshold_action(
                row["price_EUR_per_MWh"],
                cheap_threshold,
                expensive_threshold,
            )
            hourly_results.append(_simulate_hour(row, plant, action, duration_h))

    return pd.DataFrame(hourly_results)


def run_seasonal_day_ahead_strategy(
    market_data,
    plant,
    previous_year_market_data,
    cheap_percentile=25,
    expensive_percentile=75,
    min_reservoir_low_value_month=0.05,
    min_reservoir_high_value_month=0.85,
    top_price_fraction_for_water_value=0.20,
    minimum_daily_spread_EUR_per_MWh=0.0,
    target_reservoir_buffer_fraction=0.0,
    seasonal_generation_premium_fraction=0.0,
    reserve_release_percentile=100,
    seasonal_refill_pump_percentile=30,
):
    """Dispatch with historical monthly water values and day-ahead prices.

    Previous-year prices are used only to estimate monthly water values. Within
    each current-year day, the strategy still sees only that day's 24-hour price
    window.

    The operation is intentionally closer to a real pumped-storage reservoir:
    it follows a seasonal storage trajectory and generates in daily peak hours.
    Historically cheap months get a higher storage target, so the plant may
    pump in moderately cheap hours to refill before valuable months.
    """
    monthly_water_value = calculate_monthly_water_values(
        previous_year_market_data,
        top_price_fraction_for_water_value=top_price_fraction_for_water_value,
    )
    normalized_water_value = normalize_monthly_values(monthly_water_value)
    monthly_min_storage = _monthly_storage_targets(
        plant=plant,
        normalized_water_value=normalized_water_value,
        low_fraction=min_reservoir_low_value_month,
        high_fraction=min_reservoir_high_value_month,
    )

    hourly_results = []
    duration_h = 1.0

    for _, day_data in market_data.groupby(market_data["datetime"].dt.date, sort=True):
        cheap_threshold, expensive_threshold = percentile_thresholds(
            day_data["price_EUR_per_MWh"],
            cheap_percentile=cheap_percentile,
            expensive_percentile=expensive_percentile,
        )
        _, reserve_release_threshold = percentile_thresholds(
            day_data["price_EUR_per_MWh"],
            cheap_percentile=cheap_percentile,
            expensive_percentile=reserve_release_percentile,
        )
        _, refill_pump_threshold = percentile_thresholds(
            day_data["price_EUR_per_MWh"],
            cheap_percentile=cheap_percentile,
            expensive_percentile=seasonal_refill_pump_percentile,
        )
        month = int(day_data["datetime"].iloc[0].month)
        monthly_min_storage_MWh = monthly_min_storage.get(month, plant.min_storage_MWh)
        normalized_month_value = normalized_water_value.get(month, 0.5)
        daily_peak_value = float(day_data["price_EUR_per_MWh"].max())
        daily_spread_is_profitable = (
            expensive_threshold * plant.roundtrip_efficiency
            >= cheap_threshold + minimum_daily_spread_EUR_per_MWh
        )
        target_storage_MWh = min(
            plant.max_storage_MWh,
            monthly_min_storage_MWh
            + target_reservoir_buffer_fraction * plant.storage_capacity_MWh,
        )

        for _, row in day_data.iterrows():
            price = row["price_EUR_per_MWh"]
            action = _seasonal_day_ahead_action(
                price=price,
                cheap_threshold=cheap_threshold,
                expensive_threshold=expensive_threshold,
                reserve_release_threshold=reserve_release_threshold,
                daily_peak_value=daily_peak_value,
                normalized_month_value=normalized_month_value,
                seasonal_generation_premium_fraction=seasonal_generation_premium_fraction,
                storage_MWh=plant.storage_MWh,
                technical_min_storage_MWh=plant.min_storage_MWh,
                monthly_min_storage_MWh=monthly_min_storage_MWh,
                target_storage_MWh=target_storage_MWh,
                daily_spread_is_profitable=daily_spread_is_profitable,
                refill_pump_threshold=refill_pump_threshold,
            )
            generation_min_storage_MWh = monthly_min_storage_MWh
            if price >= reserve_release_threshold:
                generation_min_storage_MWh = max(
                    plant.min_storage_MWh,
                    0.5 * monthly_min_storage_MWh,
                )

            hourly_results.append(
                _simulate_hour(
                    row,
                    plant,
                    action,
                    duration_h,
                    min_storage_override_MWh=generation_min_storage_MWh,
                )
            )

    return pd.DataFrame(hourly_results)


def _daily_threshold_action(price, cheap_threshold, expensive_threshold):
    if cheap_threshold >= expensive_threshold:
        return "idle"
    if price <= cheap_threshold:
        return "pump"
    if price >= expensive_threshold:
        return "generate"
    return "idle"


def _seasonal_day_ahead_action(
    price,
    cheap_threshold,
    expensive_threshold,
    reserve_release_threshold,
    daily_peak_value,
    normalized_month_value,
    seasonal_generation_premium_fraction,
    storage_MWh,
    technical_min_storage_MWh,
    monthly_min_storage_MWh,
    target_storage_MWh,
    daily_spread_is_profitable,
    refill_pump_threshold,
):
    if cheap_threshold >= expensive_threshold:
        return "idle"

    # Keep a seasonal reserve, but use water above that reserve during daily
    # price peaks. The historical monthly signal only adds a limited premium
    # above the daily expensive threshold in valuable months.
    seasonal_generation_threshold = expensive_threshold + (
        normalized_month_value
        * seasonal_generation_premium_fraction
        * max(0.0, daily_peak_value - expensive_threshold)
    )
    if (
        price >= seasonal_generation_threshold
        and storage_MWh > monthly_min_storage_MWh
    ):
        return "generate"
    if price >= reserve_release_threshold and storage_MWh > technical_min_storage_MWh:
        return "generate"

    # In refill months, pump toward the seasonal target even if the same-day
    # spread is not perfect. This mimics a reservoir rebuilding water value
    # ahead of historically more valuable months.
    if storage_MWh < monthly_min_storage_MWh and price <= refill_pump_threshold:
        return "pump"

    # Otherwise, pump only when the same day contains enough sell-price upside
    # to cover losses.
    if (
        price <= cheap_threshold
        and daily_spread_is_profitable
        and storage_MWh < target_storage_MWh
    ):
        return "pump"

    return "idle"


def _monthly_storage_targets(
    plant,
    normalized_water_value,
    low_fraction,
    high_fraction,
):
    if not 0 <= low_fraction <= high_fraction <= 1:
        raise ValueError(
            "Monthly reservoir target fractions must satisfy "
            "0 <= low <= high <= 1."
        )

    targets = {}
    for month, normalized_value in normalized_water_value.items():
        # Low historical price months are refill months, so they receive the
        # higher storage target. High-value months may draw the reservoir down.
        target_fraction = high_fraction - normalized_value * (
            high_fraction - low_fraction
        )
        target_MWh = plant.storage_capacity_MWh * target_fraction
        targets[month] = max(
            plant.min_storage_MWh,
            min(target_MWh, plant.max_storage_MWh),
        )
    return targets


def _simulate_hour(
    row,
    plant,
    action,
    duration_h,
    min_storage_override_MWh=None,
):
    price = row["price_EUR_per_MWh"]
    pump_MWh = 0.0
    generation_MWh = 0.0

    if action == "pump":
        pump_MWh = plant.pump(plant.pump_power_MW, duration_h)
        if pump_MWh == 0:
            action = "idle"
    elif action == "generate":
        generation_MWh = _generate_with_optional_minimum(
            plant,
            plant.turbine_power_MW,
            duration_h,
            min_storage_override_MWh=min_storage_override_MWh,
        )
        if generation_MWh == 0:
            action = "idle"

    cost_EUR = pump_MWh * price
    revenue_EUR = generation_MWh * price
    profit_EUR = revenue_EUR - cost_EUR

    return {
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


def _generate_with_optional_minimum(
    plant,
    power_MW,
    duration_h,
    min_storage_override_MWh=None,
):
    if min_storage_override_MWh is None:
        return plant.generate(power_MW, duration_h)

    original_min_storage_MWh = plant.min_storage_MWh
    plant.min_storage_MWh = max(
        original_min_storage_MWh,
        float(min_storage_override_MWh),
    )
    try:
        return plant.generate(power_MW, duration_h)
    finally:
        plant.min_storage_MWh = original_min_storage_MWh
