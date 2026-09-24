"""Yield curve: fare vs booking-advance window."""
import pandas as pd


def yield_curve(quotes: pd.DataFrame) -> pd.DataFrame:
    """Mean fare per period per advance window (one line per window on the dashboard)."""
    return (
        quotes.groupby(["period", "advance_days"], as_index=False)["amount"]
        .mean()
        .rename(columns={"amount": "avg_fare"})
    )


def advance_premium(quotes: pd.DataFrame, short: int = 1, long: int = 30) -> float:
    """Ratio of the mean `short`-day fare to the mean `long`-day fare, e.g. 2.1 = 110% premium."""
    means = quotes.groupby("advance_days")["amount"].mean()
    return float(means[short] / means[long])
