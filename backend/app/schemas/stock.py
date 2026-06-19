from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StockSearchItem(BaseModel):
    symbol: str
    name: str | None = None
    price: float | None = None
    change_percent: float | None = None


class StockBasicInfoOut(BaseModel):
    symbol: str
    name: str | None = None
    market: str | None = None
    industry: str | None = None
    listed_date: str | None = None
    total_share: float | None = None
    float_share: float | None = None
    total_market_value: float | None = None
    float_market_value: float | None = None


class StockQuoteOut(BaseModel):
    symbol: str
    name: str | None = None
    price: float | None = None
    change_percent: float | None = None
    change_amount: float | None = None
    volume: float | None = None
    amount: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    previous_close: float | None = None
    turnover_rate: float | None = None
    source: str | None = None
    source_timestamp: str | None = None
    timestamp: datetime


class KLineItem(BaseModel):
    trade_date: date
    open: float | None = None
    close: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    amount: float | None = None
    amplitude: float | None = None
    change_percent: float | None = None
    change_amount: float | None = None
    turnover_rate: float | None = None
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    rsi: float | None = None


class LatestIndicators(BaseModel):
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    rsi: float | None = None


class PredictionOut(BaseModel):
    symbol: str
    close_price: float | None = None
    up_probability: float = Field(ge=0, le=100)
    down_probability: float = Field(ge=0, le=100)
    risk_level: str
    reasons: list[str]
    disclaimer: str
    generated_at: datetime


class PredictionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    close_price: float | None = None
    up_probability: float
    down_probability: float
    risk_level: str
    reasons: list[str] | None = None
    disclaimer: str
    created_at: datetime


class StockAnalysisOut(BaseModel):
    basic_info: StockBasicInfoOut
    quote: StockQuoteOut
    latest_indicators: LatestIndicators
    prediction: PredictionOut
    history: list[KLineItem]


class ApiMessage(BaseModel):
    message: str
