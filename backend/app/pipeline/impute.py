"""Carry-forward imputation of missing fares, flagged as imputed."""
from collections.abc import Sequence
from datetime import date

import numpy as np
import pandas as pd

from app.models import QUOTE_KEY


def _geometric_mean(amounts: pd.Series) -> float:
    if len(amounts) == 1:  # the usual case: one observation per day, kept exact
        return float(amounts.iloc[0])
    return float(np.exp(np.log(amounts).mean()))


def carry_forward(fares: pd.DataFrame, periods: Sequence[date]) -> pd.DataFrame:
    """One row per quote series per period, gaps filled with the series' last observed fare.

    A series observed several times in one period (the collector ran more than once that day)
    gets the geometric mean of those observations, consistent with Jevons; never the arithmetic
    mean, and not the minimum, which would drift down the more often the collector runs.
    Filled rows get imputed=True. A series stays missing before its first observation.
    """
    wide = fares.pivot_table(index="period", columns=QUOTE_KEY, values="amount", aggfunc=_geometric_mean).reindex(periods)
    filled = wide.ffill()
    levels = list(range(len(QUOTE_KEY)))
    quotes = filled.stack(levels).rename("amount").to_frame()
    quotes["imputed"] = (wide.isna() & filled.notna()).stack(levels)
    return quotes.dropna(subset=["amount"]).reset_index()
