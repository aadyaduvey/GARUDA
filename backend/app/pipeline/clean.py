"""Outlier filter: drop fares < INR 500 or > INR 50,000 before indexing."""
import pandas as pd

MIN_FARE = 500
MAX_FARE = 50_000


def drop_outliers(fares: pd.DataFrame) -> pd.DataFrame:
    return fares[fares["amount"].between(MIN_FARE, MAX_FARE)]
