"""National index: DGCA-weighted arithmetic mean of route indices (Young / modified Laspeyres)."""
from collections.abc import Mapping

import pandas as pd


def national_index(route_index: Mapping[int, float], weights: Mapping[int, float]) -> float:
    """Weighted mean of route indices, weights renormalised over the routes present."""
    if not route_index:
        raise ValueError("no route indices to aggregate")
    total = sum(weights[r] for r in route_index)
    if total <= 0:
        raise ValueError("route weights must sum to a positive number")
    return sum(weights[r] * index for r, index in route_index.items()) / total


def national_series(route_indices: pd.DataFrame, weights: Mapping[int, float]) -> pd.DataFrame:
    """National index per period from (route_id, period, jevons_index) rows."""
    return (
        route_indices.groupby("period")
        .apply(lambda g: national_index(dict(zip(g["route_id"], g["jevons_index"])), weights), include_groups=False)
        .rename("national_index")
        .reset_index()
    )
