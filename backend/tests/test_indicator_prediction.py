import pandas as pd

from app.services.indicator_service import IndicatorService
from app.services.prediction_service import PredictionService


def test_indicator_service_adds_expected_columns():
    frame = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=30, freq="D"),
            "open": range(10, 40),
            "close": range(11, 41),
            "high": range(12, 42),
            "low": range(9, 39),
            "volume": [1000] * 30,
            "amount": [10000] * 30,
            "amplitude": [1.0] * 30,
            "change_percent": [0.5] * 30,
            "change_amount": [0.1] * 30,
            "turnover_rate": [1.2] * 30,
        }
    )

    enriched = IndicatorService().enrich(frame)

    for column in ["ma5", "ma10", "ma20", "macd", "macd_signal", "macd_hist", "rsi"]:
        assert column in enriched.columns
    assert enriched.iloc[-1]["ma5"] > enriched.iloc[-1]["ma20"]


def test_prediction_service_returns_probabilities_and_disclaimer():
    frame = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=30, freq="D"),
            "close": range(11, 41),
            "change_percent": [0.5] * 30,
        }
    )
    enriched = IndicatorService().enrich(frame)
    quote = {"price": 40.0, "change_percent": 1.2}

    prediction = PredictionService().predict("000001", quote, enriched)

    assert prediction["up_probability"] + prediction["down_probability"] == 100
    assert prediction["risk_level"] in {"低", "中", "高"}
    assert prediction["disclaimer"] == "仅供学习研究，不构成投资建议。"
    assert prediction["reasons"]

