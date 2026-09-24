"""Jevons elementary index: geometric mean of price relatives. NEVER the arithmetic mean."""
from collections.abc import Sequence
from datetime import date

import numpy as np
import pandas as pd

from app.models import QUOTE_KEY


def jevons(prices: Sequence[float], base_prices: Sequence[float]) -> float:
    """100 x geometric mean of p_t / p_0 over matched quotes."""
    p = np.asarray(prices, dtype=float)
    p0 = np.asarray(base_prices, dtype=float)
    if p.ndim != 1 or p.shape != p0.shape:
        raise ValueError("prices and base_prices must be matched 1-D sequences")
    if p.size == 0:
        raise ValueError("no matched price quotes")
    if (p <= 0).any() or (p0 <= 0).any():
        raise ValueError("prices must be positive")
    return float(100 * np.exp(np.log(p / p0).mean()))


def route_indices(quotes: pd.DataFrame, base_periods: Sequence[date]) -> pd.DataFrame:
    """Jevons index per route per period.

    `quotes` has one row per quote series per period (QUOTE_KEY, period, amount).
    Each series' base price is the geometric mean of its fares over `base_periods`;
    series with no fare in the base window are excluded (unmatched).
    """
    in_base = quotes[quotes["period"].isin(base_periods)]
    base = in_base.groupby(QUOTE_KEY)["amount"].agg(lambda a: np.exp(np.log(a).mean())).rename("base_amount")
    matched = quotes.join(base, on=QUOTE_KEY, how="inner")
    return (
        matched.groupby(["route_id", "period"])
        .apply(lambda g: jevons(g["amount"], g["base_amount"]), include_groups=False)
        .rename("jevons_index")
        .reset_index()
    )
