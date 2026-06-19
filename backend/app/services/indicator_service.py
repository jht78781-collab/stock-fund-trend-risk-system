import numpy as np
import pandas as pd


class IndicatorService:
    def enrich(self, history: pd.DataFrame) -> pd.DataFrame:
        frame = history.copy()
        frame = self._ensure_numeric(frame)

        close = frame["close"]
        frame["ma5"] = close.rolling(window=5, min_periods=1).mean()
        frame["ma10"] = close.rolling(window=10, min_periods=1).mean()
        frame["ma20"] = close.rolling(window=20, min_periods=1).mean()

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        frame["macd"] = ema12 - ema26
        frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()
        frame["macd_hist"] = frame["macd"] - frame["macd_signal"]
        frame["rsi"] = self._calculate_rsi(close, period=14)
        return frame

    def _ensure_numeric(self, frame: pd.DataFrame) -> pd.DataFrame:
        numeric_columns = [
            "open",
            "close",
            "high",
            "low",
            "volume",
            "amount",
            "amplitude",
            "change_percent",
            "change_amount",
            "turnover_rate",
        ]
        for column in numeric_columns:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.where(avg_loss != 0, 100)
        rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50)
        return rsi

