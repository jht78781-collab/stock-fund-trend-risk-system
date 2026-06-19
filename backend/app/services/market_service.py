import logging
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.stock_repository import StockRepository
from app.services.akshare_service import AKShareService
from app.services.indicator_service import IndicatorService
from app.services.prediction_service import PredictionService
from app.utils.date_utils import china_now, default_start_date, normalize_akshare_date

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.repository = StockRepository(db) if db is not None else None
        self.akshare = AKShareService()
        self.indicator = IndicatorService()
        self.predictor = PredictionService()

    def search_stocks(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        return self.akshare.search_stocks(keyword=keyword, limit=limit)

    def list_stock_universe(self) -> list[dict[str, Any]]:
        return self.akshare.get_stock_universe()

    def get_realtime_quote(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = self.akshare.normalize_symbol(symbol)
        return self.akshare.get_quote(normalized_symbol)

    def get_history(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "qfq",
        persist: bool = True,
    ) -> list[dict[str, Any]]:
        normalized_symbol = self.akshare.normalize_symbol(symbol)
        start, end = self._resolve_dates(start_date, end_date)
        history = self.akshare.get_history(normalized_symbol, start, end, adjust)
        enriched = self.indicator.enrich(history)
        rows = self._history_rows(enriched, normalized_symbol)

        if persist:
            self._safe_persist_history(rows)

        return rows

    def analyze_stock(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "qfq",
    ) -> dict[str, Any]:
        normalized_symbol = self.akshare.normalize_symbol(symbol)
        start, end = self._resolve_dates(start_date, end_date)

        quote = self.akshare.get_quote(normalized_symbol)
        basic_info = self.akshare.get_basic_info(normalized_symbol)
        history = self.akshare.get_history(normalized_symbol, start, end, adjust)
        enriched = self.indicator.enrich(history)
        prediction = self.predictor.predict(normalized_symbol, quote, enriched)

        history_rows = self._history_rows(enriched, normalized_symbol)
        latest_indicators = self._latest_indicators(enriched)

        self._safe_persist_basic_info(basic_info)
        self._safe_persist_history(history_rows)
        self._safe_persist_prediction(prediction)

        return {
            "basic_info": basic_info,
            "quote": quote,
            "latest_indicators": latest_indicators,
            "prediction": prediction,
            "history": history_rows,
        }

    def list_predictions(self, symbol: str, limit: int = 20) -> list[Any]:
        if self.repository is None:
            return []
        normalized_symbol = self.akshare.normalize_symbol(symbol)
        return self.repository.list_predictions(normalized_symbol, limit=limit)

    def _resolve_dates(self, start_date: str | None, end_date: str | None) -> tuple[str, str]:
        start = normalize_akshare_date(start_date, default_start_date())
        end = normalize_akshare_date(end_date, china_now().date())
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        return start, end

    def _history_rows(self, frame: pd.DataFrame, symbol: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            trade_date = self._to_date(row.get("trade_date"))
            if trade_date is None:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "open": self._round(row.get("open")),
                    "close": self._round(row.get("close")),
                    "high": self._round(row.get("high")),
                    "low": self._round(row.get("low")),
                    "volume": self._round(row.get("volume"), digits=0),
                    "amount": self._round(row.get("amount"), digits=2),
                    "amplitude": self._round(row.get("amplitude")),
                    "change_percent": self._round(row.get("change_percent")),
                    "change_amount": self._round(row.get("change_amount")),
                    "turnover_rate": self._round(row.get("turnover_rate")),
                    "ma5": self._round(row.get("ma5")),
                    "ma10": self._round(row.get("ma10")),
                    "ma20": self._round(row.get("ma20")),
                    "macd": self._round(row.get("macd")),
                    "macd_signal": self._round(row.get("macd_signal")),
                    "macd_hist": self._round(row.get("macd_hist")),
                    "rsi": self._round(row.get("rsi")),
                }
            )
        return rows

    def _latest_indicators(self, frame: pd.DataFrame) -> dict[str, float | None]:
        if frame.empty:
            return {
                "ma5": None,
                "ma10": None,
                "ma20": None,
                "macd": None,
                "macd_signal": None,
                "macd_hist": None,
                "rsi": None,
            }
        latest = frame.iloc[-1]
        return {
            "ma5": self._round(latest.get("ma5")),
            "ma10": self._round(latest.get("ma10")),
            "ma20": self._round(latest.get("ma20")),
            "macd": self._round(latest.get("macd")),
            "macd_signal": self._round(latest.get("macd_signal")),
            "macd_hist": self._round(latest.get("macd_hist")),
            "rsi": self._round(latest.get("rsi")),
        }

    def _safe_persist_basic_info(self, basic_info: dict[str, Any]) -> None:
        if self.repository is None:
            return
        try:
            self.repository.upsert_basic_info(basic_info)
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.warning("Failed to persist stock basic info: %s", exc)

    def _safe_persist_history(self, rows: list[dict[str, Any]]) -> None:
        if self.repository is None or not rows:
            return
        try:
            self.repository.upsert_history(rows)
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.warning("Failed to persist historical quotes: %s", exc)

    def _safe_persist_prediction(self, prediction: dict[str, Any]) -> None:
        if self.repository is None:
            return
        try:
            self.repository.create_prediction(
                {
                    "symbol": prediction["symbol"],
                    "close_price": prediction["close_price"],
                    "up_probability": prediction["up_probability"],
                    "down_probability": prediction["down_probability"],
                    "risk_level": prediction["risk_level"],
                    "reasons": prediction["reasons"],
                    "disclaimer": prediction["disclaimer"],
                }
            )
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.warning("Failed to persist prediction record: %s", exc)

    def _to_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return pd.to_datetime(value).date()
        except (TypeError, ValueError):
            return None

    def _round(self, value: Any, digits: int = 4) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return round(float(value), digits)
        except (TypeError, ValueError):
            return None
