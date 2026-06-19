from typing import Any

import pandas as pd

from app.core.config import settings
from app.utils.date_utils import china_now


class PredictionService:
    def predict(self, symbol: str, quote: dict[str, Any], history: pd.DataFrame) -> dict[str, Any]:
        valid_history = history.dropna(subset=["close"]).copy()
        if valid_history.empty:
            return self._fallback_prediction(symbol, quote)

        latest = valid_history.iloc[-1]
        recent = valid_history.tail(20)

        score = 50.0
        reasons: list[str] = []
        risk_flags: list[str] = []

        close = self._to_float(latest.get("close"))
        ma5 = self._to_float(latest.get("ma5"))
        ma10 = self._to_float(latest.get("ma10"))
        ma20 = self._to_float(latest.get("ma20"))
        macd = self._to_float(latest.get("macd"))
        macd_signal = self._to_float(latest.get("macd_signal"))
        macd_hist = self._to_float(latest.get("macd_hist"))
        rsi = self._to_float(latest.get("rsi"))
        change_percent = self._to_float(quote.get("change_percent")) or self._to_float(
            latest.get("change_percent")
        )

        if self._has_values(close, ma5, ma10, ma20):
            if close >= ma5 >= ma10 >= ma20:
                score += 15
                reasons.append("价格位于 MA5、MA10、MA20 上方，短期趋势偏强")
            elif close <= ma5 <= ma10 <= ma20:
                score -= 15
                reasons.append("价格位于 MA5、MA10、MA20 下方，短期趋势偏弱")
            elif close >= ma20:
                score += 6
                reasons.append("价格仍在 MA20 上方，中期趋势有支撑")
            else:
                score -= 6
                reasons.append("价格跌破 MA20，中期趋势承压")

        if self._has_values(macd, macd_signal, macd_hist):
            if macd > macd_signal and macd_hist > 0:
                score += 10
                reasons.append("MACD 位于信号线上方且柱体为正，动能偏多")
            elif macd < macd_signal and macd_hist < 0:
                score -= 10
                reasons.append("MACD 位于信号线下方且柱体为负，动能偏空")

        if rsi is not None:
            if rsi >= 75:
                score -= 8
                risk_flags.append("RSI 高于 75，存在短线过热风险")
                reasons.append("RSI 处于超买区间，追高胜率下降")
            elif rsi >= 60:
                score += 5
                reasons.append("RSI 位于强势区间，买盘动能尚可")
            elif rsi <= 25:
                score += 4
                risk_flags.append("RSI 低于 25，波动和反抽不确定性较高")
                reasons.append("RSI 处于超卖区间，存在技术反抽可能")
            elif rsi <= 40:
                score -= 5
                reasons.append("RSI 位于弱势区间，短线动能不足")

        if change_percent is not None:
            if change_percent >= 3:
                score += 5
                risk_flags.append("当日涨幅较大，需警惕回落")
                reasons.append("当日涨幅较大，市场短线情绪偏强")
            elif change_percent <= -3:
                score -= 5
                risk_flags.append("当日跌幅较大，波动风险上升")
                reasons.append("当日跌幅较大，市场短线情绪偏弱")

        volatility = self._calculate_volatility(recent)
        if volatility is not None:
            if volatility >= 3:
                risk_flags.append(f"近 20 日涨跌幅标准差约 {volatility:.2f}%，波动偏高")
            elif volatility <= 1.2:
                reasons.append("近 20 日波动较低，走势相对平稳")

        up_probability = round(self._clamp(score, 15, 85), 2)
        down_probability = round(100 - up_probability, 2)
        risk_level = self._risk_level(volatility, change_percent, risk_flags)

        if not reasons:
            reasons.append("指标信号不明显，模型维持中性判断")

        return {
            "symbol": symbol,
            "close_price": close or self._to_float(quote.get("price")),
            "up_probability": up_probability,
            "down_probability": down_probability,
            "risk_level": risk_level,
            "reasons": reasons + risk_flags,
            "disclaimer": settings.RISK_NOTICE,
            "generated_at": china_now().isoformat(),
        }

    def _fallback_prediction(self, symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "close_price": self._to_float(quote.get("price")),
            "up_probability": 50.0,
            "down_probability": 50.0,
            "risk_level": "中",
            "reasons": ["历史行情不足，暂按中性概率输出"],
            "disclaimer": settings.RISK_NOTICE,
            "generated_at": china_now().isoformat(),
        }

    def _calculate_volatility(self, recent: pd.DataFrame) -> float | None:
        if "change_percent" not in recent.columns:
            return None
        series = pd.to_numeric(recent["change_percent"], errors="coerce").dropna()
        if len(series) < 5:
            return None
        return float(series.std())

    def _risk_level(
        self,
        volatility: float | None,
        change_percent: float | None,
        risk_flags: list[str],
    ) -> str:
        if len(risk_flags) >= 2:
            return "高"
        if volatility is not None and volatility >= 3:
            return "高"
        if change_percent is not None and abs(change_percent) >= 6:
            return "高"
        if risk_flags:
            return "中"
        if volatility is not None and volatility >= 1.8:
            return "中"
        return "低"

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _has_values(self, *values: float | None) -> bool:
        return all(value is not None for value in values)

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

