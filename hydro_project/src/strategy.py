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
