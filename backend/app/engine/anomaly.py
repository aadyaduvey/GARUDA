"""Anomaly detection, per route: z-score > 2 against the preceding 7 days AND a material (>= 5%) rise.

The materiality floor stops everyday 1-2% wobble on a calm week from tripping the z-score.
"""
import pandas as pd

Z_THRESHOLD = 2.0
MIN_RISE = 0.05  # index must be at least 5% above the preceding window's mean
WINDOW = 7


def rolling_zscore(series: pd.Series, window: int = WINDOW) -> pd.Series:
    """z of each value against the mean/std of the `window` values before it. NaN until a full window exists."""
    prior = series.shift(1).rolling(window, min_periods=window)
    return (series - prior.mean()) / prior.std()


def rolling_rise(series: pd.Series, window: int = WINDOW) -> pd.Series:
    """Fractional change of each value vs the mean of the `window` values before it."""
    return series / series.shift(1).rolling(window, min_periods=window).mean() - 1


def flag_anomalies(
    route_indices: pd.DataFrame, threshold: float = Z_THRESHOLD, min_rise: float = MIN_RISE, window: int = WINDOW
) -> pd.DataFrame:
    """Add z_score, rise and anomaly_flag columns to (route_id, period, jevons_index) rows."""
    out = route_indices.sort_values(["route_id", "period"]).copy()
    by_route = out.groupby("route_id")["jevons_index"]
    out["z_score"] = by_route.transform(lambda s: rolling_zscore(s, window))
    out["rise"] = by_route.transform(lambda s: rolling_rise(s, window))
    out["anomaly_flag"] = (out["z_score"] > threshold) & (out["rise"] >= min_rise)
    return out.reset_index(drop=True)
