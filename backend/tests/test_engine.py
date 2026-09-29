from datetime import date

import pandas as pd
import pytest

from app.engine.aggregate import national_index, national_series
from app.engine.anomaly import flag_anomalies
from app.engine.jevons import jevons, route_indices
from app.engine.yield_curve import advance_premium, yield_curve
from app.pipeline.clean import drop_outliers
from app.pipeline.impute import carry_forward

D0, D1, D2 = date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)


def quote(route_id: int, airline_id: int, period: date, amount: float, advance_days: int = 30) -> dict:
    return dict(route_id=route_id, airline_id=airline_id, advance_days=advance_days, dep_dow="TUE", period=period, amount=amount)


# --- Jevons: the hand-checkable fixture -------------------------------------


def test_jevons_is_geometric_not_arithmetic_mean() -> None:
    # (1.1 * 1.2 * 1.3) ** (1/3) = 1.19722... -> 119.72; the arithmetic mean would give 120.
    index = jevons([110, 120, 130], [100, 100, 100])
    assert index == pytest.approx(119.72, abs=0.005)
    assert index != pytest.approx(120.0, abs=0.1)


def test_jevons_unchanged_prices_give_100() -> None:
    assert jevons([4800, 5200], [4800, 5200]) == pytest.approx(100.0)


@pytest.mark.parametrize(
    "prices, base",
    [([], []), ([100, 0], [100, 100]), ([100, 100], [100, 0]), ([100], [100, 100])],
    ids=["empty", "zero-price", "zero-base", "unmatched"],
)
def test_jevons_rejects_bad_input(prices: list, base: list) -> None:
    with pytest.raises(ValueError):
        jevons(prices, base)


def test_route_indices_use_base_period_prices() -> None:
    quotes = pd.DataFrame(
        [quote(1, 1, D0, 100), quote(1, 2, D0, 100), quote(1, 1, D1, 110), quote(1, 2, D1, 120)]
    )
    out = route_indices(quotes, base_periods=[D0]).set_index("period")["jevons_index"]
    assert out[D0] == pytest.approx(100.0)
    assert out[D1] == pytest.approx(100 * (1.1 * 1.2) ** 0.5)


# --- National aggregation ---------------------------------------------------


def test_national_index_is_weighted_arithmetic_mean() -> None:
    assert national_index({1: 110.0, 2: 100.0}, {1: 0.75, 2: 0.25}) == pytest.approx(107.5)


def test_national_index_renormalises_when_a_route_is_missing() -> None:
    assert national_index({1: 110.0}, {1: 0.75, 2: 0.25}) == pytest.approx(110.0)


def test_national_series_per_period() -> None:
    routes = pd.DataFrame(
        {"route_id": [1, 2, 1, 2], "period": [D0, D0, D1, D1], "jevons_index": [100.0, 100.0, 110.0, 100.0]}
    )
    out = national_series(routes, {1: 0.75, 2: 0.25}).set_index("period")["national_index"]
    assert out[D0] == pytest.approx(100.0)
    assert out[D1] == pytest.approx(107.5)


# --- Anomaly ----------------------------------------------------------------


def test_spike_after_a_full_window_is_flagged() -> None:
    values = [100, 101, 99, 100, 101, 99, 100, 150]
    routes = pd.DataFrame({"route_id": 1, "period": pd.date_range("2026-01-01", periods=8).date, "jevons_index": values})
    flags = flag_anomalies(routes)["anomaly_flag"].tolist()
    assert flags == [False] * 7 + [True]


def test_small_move_on_a_calm_week_is_not_flagged() -> None:
    # 102 is z ~ 2.6 vs a near-flat week, but only a 2% rise: below the 5% materiality floor.
    values = [100, 100.5, 99.5, 100, 100.5, 99.5, 100, 102]
    routes = pd.DataFrame({"route_id": 1, "period": pd.date_range("2026-01-01", periods=8).date, "jevons_index": values})
    out = flag_anomalies(routes)
    assert out["z_score"].iloc[-1] > 2
    assert not out["anomaly_flag"].any()


# --- Pipeline ---------------------------------------------------------------


def test_drop_outliers_keeps_bounds_inclusive() -> None:
    fares = pd.DataFrame({"amount": [499, 500, 50_000, 50_001]})
    assert drop_outliers(fares)["amount"].tolist() == [500, 50_000]


def test_carry_forward_fills_gap_and_flags_it() -> None:
    fares = pd.DataFrame([quote(1, 1, D0, 100), quote(1, 1, D2, 120)])
    out = carry_forward(fares, [D0, D1, D2]).set_index("period")
    assert out.loc[D1, "amount"] == 100
    assert out["imputed"].tolist() == [False, True, False]


def test_same_day_observations_combine_by_geometric_mean() -> None:
    fares = pd.DataFrame([quote(1, 1, D0, 100), quote(1, 1, D0, 121)])
    out = carry_forward(fares, [D0])
    assert out["amount"].iloc[0] == pytest.approx(110.0)  # sqrt(100 x 121), not 110.5 or 100
    assert not out["imputed"].iloc[0]


# --- Yield curve ------------------------------------------------------------


def test_yield_curve_and_premium() -> None:
    quotes = pd.DataFrame([quote(1, 1, D0, 100, advance_days=30), quote(1, 1, D0, 210, advance_days=1)])
    curve = yield_curve(quotes).set_index("advance_days")["avg_fare"]
    assert curve[1] == 210 and curve[30] == 100
    assert advance_premium(quotes) == pytest.approx(2.1)
