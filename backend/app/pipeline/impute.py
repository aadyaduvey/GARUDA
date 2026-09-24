"""Carry-forward imputation of missing fares, flagged as imputed."""
from collections.abc import Sequence
from datetime import date

import pandas as pd

from app.models import QUOTE_KEY


def carry_forward(fares: pd.DataFrame, periods: Sequence[date]) -> pd.DataFrame:
    """One row per quote series per period, gaps filled with the series' last observed fare.

    Takes the lowest fare when a series has several in one period. Filled rows get
    imputed=True. A series stays missing before its first observation.
    """
    wide = fares.pivot_table(index="period", columns=QUOTE_KEY, values="amount", aggfunc="min").reindex(periods)
    filled = wide.ffill()
    levels = list(range(len(QUOTE_KEY)))
    quotes = filled.stack(levels).rename("amount").to_frame()
    quotes["imputed"] = (wide.isna() & filled.notna()).stack(levels)
    return quotes.dropna(subset=["amount"]).reset_index()
