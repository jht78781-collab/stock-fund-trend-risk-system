import logging
import math
import re
from datetime import datetime
from typing import Any

import pandas as pd
import requests

from app.core.cache import cache
from app.core.config import settings
from app.services.exceptions import DataSourceError, StockNotFoundError
from app.utils.date_utils import CHINA_TZ, china_now

logger = logging.getLogger(__name__)

SYMBOL_PATTERN = re.compile(r"(\d{6})")


class AKShareService:
    EASTMONEY_FIELDS = (
        "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,"
        "f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    )

    def normalize_symbol(self, symbol: str) -> str:
        match = SYMBOL_PATTERN.search(symbol.strip())
        if not match:
            raise StockNotFoundError("股票代码必须包含 6 位数字")
        return match.group(1)

    def search_stocks(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        normalized_keyword = keyword.strip().lower()
        records = self._get_spot_records()
        results: list[dict[str, Any]] = []

        for record in records:
            symbol = str(record.get("代码", "")).zfill(6)
            name = str(record.get("名称", ""))
            if normalized_keyword in symbol.lower() or normalized_keyword in name.lower():
                results.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "price": self._to_float(record.get("最新价")),
                        "change_percent": self._to_float(record.get("涨跌幅")),
                    }
                )
            if len(results) >= limit:
                break
        return results

    def get_quote(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = self.normalize_symbol(symbol)
        cache_key = f"stock:quote:{normalized_symbol}"
        cached = cache.get_json(cache_key)
        if cached is not None:
            return cached

        try:
            quote = self._get_quote_direct(normalized_symbol)
            cache.set_json(cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS)
            return quote
        except requests.RequestException as exc:
            logger.warning("Eastmoney single-stock quote failed, trying Tencent quote: %s", exc)

        try:
            quote = self._get_quote_tencent(normalized_symbol)
            cache.set_json(cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS)
            return quote
        except requests.RequestException as exc:
            logger.warning("Tencent single-stock quote failed, trying AKShare spot list: %s", exc)

        records = self._get_spot_records()
        for record in records:
            record_symbol = str(record.get("代码", "")).zfill(6)
            if record_symbol == normalized_symbol:
                quote = self._quote_from_spot_record(normalized_symbol, record)
                cache.set_json(cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS)
                return quote

        raise StockNotFoundError(f"未找到股票代码：{normalized_symbol}")

    def get_basic_info(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = self.normalize_symbol(symbol)
        cache_key = f"stock:basic:{normalized_symbol}"
        cached = cache.get_json(cache_key)
        if cached is not None:
            return cached

        info = {
            "symbol": normalized_symbol,
            "name": None,
            "market": self._infer_market(normalized_symbol),
            "industry": None,
            "listed_date": None,
            "total_share": None,
            "float_share": None,
            "total_market_value": None,
            "float_market_value": None,
        }

        try:
            import akshare as ak

            frame = ak.stock_individual_info_em(symbol=normalized_symbol)
            if not frame.empty:
                records = frame.where(pd.notna(frame), None).to_dict(orient="records")
                info_map = {str(item.get("item")): item.get("value") for item in records}
                info.update(
                    {
                        "name": self._to_text(
                            info_map.get("股票简称")
                            or info_map.get("股票名称")
                            or info_map.get("证券简称")
                        ),
                        "industry": self._to_text(info_map.get("行业")),
                        "listed_date": self._to_text(info_map.get("上市时间")),
                        "total_share": self._to_float(info_map.get("总股本")),
                        "float_share": self._to_float(info_map.get("流通股")),
                        "total_market_value": self._to_float(info_map.get("总市值")),
                        "float_market_value": self._to_float(info_map.get("流通市值")),
                    }
                )
        except Exception as exc:
            logger.warning("Failed to fetch stock basic info from AKShare: %s", exc)

        if not info["name"]:
            try:
                info["name"] = self.get_quote(normalized_symbol).get("name")
            except StockNotFoundError:
                pass

        cache.set_json(cache_key, info, 3600)
        return info

    def get_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        normalized_symbol = self.normalize_symbol(symbol)
        cache_key = f"stock:history:{normalized_symbol}:{start_date}:{end_date}:{adjust}"
        cached = cache.get_json(cache_key)
        if cached is not None:
            frame = pd.DataFrame(cached)
            if not frame.empty:
                frame["trade_date"] = pd.to_datetime(frame["trade_date"])
            return frame

        try:
            import akshare as ak

            frame = ak.stock_zh_a_hist(
                symbol=normalized_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception as exc:
            logger.warning("AKShare history failed, falling back to Eastmoney direct API: %s", exc)
            try:
                frame = self._get_history_direct(
                    symbol=normalized_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
            except requests.RequestException as direct_exc:
                logger.warning("Eastmoney history failed, trying Tencent history: %s", direct_exc)
                try:
                    frame = self._get_history_tencent(
                        symbol=normalized_symbol,
                        start_date=start_date,
                        end_date=end_date,
                        adjust=adjust,
                    )
                except requests.RequestException as tencent_exc:
                    if settings.ENABLE_FIXTURE_FALLBACK:
                        logger.warning("Using fixture history data because upstream failed: %s", tencent_exc)
                        frame = self._get_fixture_history_frame(
                            symbol=normalized_symbol,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    else:
                        raise DataSourceError(
                            f"AKShare、东方财富和腾讯历史行情均获取失败：{tencent_exc}"
                        ) from tencent_exc

        if frame.empty:
            raise StockNotFoundError(f"未获取到 {normalized_symbol} 的历史行情")

        normalized = self._normalize_history_frame(frame, normalized_symbol)
        cache_payload = self._serialize_frame(normalized)
        cache.set_json(cache_key, cache_payload, settings.HISTORY_CACHE_TTL_SECONDS)
        return normalized

    def _get_spot_records(self) -> list[dict[str, Any]]:
        cache_key = "stock:spot:em:all"
        cached = cache.get_json(cache_key)
        if cached is not None:
            return cached

        try:
            import akshare as ak

            frame = ak.stock_zh_a_spot_em()
        except Exception as exc:
            logger.warning("AKShare spot failed, falling back to Eastmoney direct API: %s", exc)
            try:
                records = self._get_spot_records_direct()
            except requests.RequestException as direct_exc:
                if settings.ENABLE_FIXTURE_FALLBACK:
                    logger.warning("Using fixture spot data because upstream failed: %s", direct_exc)
                    records = self._get_fixture_spot_records()
                else:
                    raise DataSourceError(
                        f"AKShare 和东方财富兜底实时行情均获取失败：{direct_exc}"
                    ) from direct_exc
            cache.set_json(cache_key, records, settings.QUOTE_CACHE_TTL_SECONDS)
            return records

        records = frame.where(pd.notna(frame), None).to_dict(orient="records")
        cache.set_json(cache_key, records, settings.QUOTE_CACHE_TTL_SECONDS)
        return records

    def _quote_from_spot_record(self, symbol: str, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "name": self._to_text(record.get("名称")),
            "price": self._to_float(record.get("最新价")),
            "change_percent": self._to_float(record.get("涨跌幅")),
            "change_amount": self._to_float(record.get("涨跌额")),
            "volume": self._to_float(record.get("成交量")),
            "amount": self._to_float(record.get("成交额")),
            "high": self._to_float(record.get("最高")),
            "low": self._to_float(record.get("最低")),
            "open": self._to_float(record.get("今开")),
            "previous_close": self._to_float(record.get("昨收")),
            "turnover_rate": self._to_float(record.get("换手率")),
            "source": "AKShare",
            "source_timestamp": None,
            "timestamp": china_now().isoformat(),
        }

    def _get_quote_direct(self, symbol: str) -> dict[str, Any]:
        params = {
            "secid": f"{self._eastmoney_market_id(symbol)}.{symbol}",
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f168,f169,f170",
        }
        data = self._eastmoney_get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params,
            fallback_urls=[
                "https://82.push2.eastmoney.com/api/qt/stock/get",
                "https://81.push2.eastmoney.com/api/qt/stock/get",
            ],
        )
        detail = data.get("data") or {}
        if not detail:
            raise DataSourceError(f"未获取到 {symbol} 的实时行情")

        price = self._eastmoney_scaled(detail.get("f43"))
        previous_close = self._eastmoney_scaled(detail.get("f60"))
        return {
            "symbol": symbol,
            "name": self._to_text(detail.get("f58")),
            "price": price,
            "change_percent": self._eastmoney_scaled(detail.get("f170")),
            "change_amount": self._eastmoney_scaled(detail.get("f169")),
            "volume": self._to_float(detail.get("f47")),
            "amount": self._to_float(detail.get("f48")),
            "high": self._eastmoney_scaled(detail.get("f44")),
            "low": self._eastmoney_scaled(detail.get("f45")),
            "open": self._eastmoney_scaled(detail.get("f46")),
            "previous_close": previous_close,
            "turnover_rate": self._eastmoney_scaled(detail.get("f168")),
            "source": "Eastmoney",
            "source_timestamp": None,
            "timestamp": china_now().isoformat(),
        }

    def _get_quote_tencent(self, symbol: str) -> dict[str, Any]:
        tencent_symbol = self._tencent_symbol(symbol)
        text = self._http_get_text("https://qt.gtimg.cn/q=" + tencent_symbol)
        if '="' not in text:
            raise DataSourceError(f"腾讯实时行情未返回有效数据：{symbol}")
        body = text.split('="', 1)[1].rsplit('"', 1)[0]
        parts = body.split("~")
        if len(parts) < 40:
            raise DataSourceError(f"腾讯实时行情字段不足：{symbol}")

        amount = None
        volume = self._to_float(parts[36] if len(parts) > 36 else parts[6])
        deal_info = parts[35].split("/") if len(parts) > 35 else []
        if len(deal_info) >= 3:
            amount = self._to_float(deal_info[2])

        return {
            "symbol": symbol,
            "name": self._to_text(parts[1]),
            "price": self._to_float(parts[3]),
            "change_percent": self._to_float(parts[32]),
            "change_amount": self._to_float(parts[31]),
            "volume": volume,
            "amount": amount,
            "high": self._to_float(parts[33]),
            "low": self._to_float(parts[34]),
            "open": self._to_float(parts[5]),
            "previous_close": self._to_float(parts[4]),
            "turnover_rate": self._to_float(parts[38]),
            "source": "Tencent",
            "source_timestamp": self._parse_tencent_timestamp(parts[30]),
            "timestamp": china_now().isoformat(),
        }

    def _get_spot_records_direct(self) -> list[dict[str, Any]]:
        params = {
            "pn": "1",
            "pz": "10000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": self.EASTMONEY_FIELDS,
        }
        data = self._eastmoney_get(
            "https://push2.eastmoney.com/api/qt/clist/get",
            params,
            fallback_urls=[
                "https://82.push2.eastmoney.com/api/qt/clist/get",
                "https://81.push2.eastmoney.com/api/qt/clist/get",
            ],
        )
        diff = data.get("data", {}).get("diff") or []
        if not diff:
            raise DataSourceError("东方财富实时行情兜底接口未返回数据")

        return [
            {
                "代码": str(item.get("f12", "")).zfill(6),
                "名称": item.get("f14"),
                "最新价": item.get("f2"),
                "涨跌幅": item.get("f3"),
                "涨跌额": item.get("f4"),
                "成交量": item.get("f5"),
                "成交额": item.get("f6"),
                "振幅": item.get("f7"),
                "换手率": item.get("f8"),
                "最高": item.get("f15"),
                "最低": item.get("f16"),
                "今开": item.get("f17"),
                "昨收": item.get("f18"),
                "总市值": item.get("f20"),
                "流通市值": item.get("f21"),
            }
            for item in diff
        ]

    def _get_history_direct(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> pd.DataFrame:
        params = {
            "secid": f"{self._eastmoney_market_id(symbol)}.{symbol}",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": self._eastmoney_adjust(adjust),
            "beg": start_date,
            "end": end_date,
        }
        data = self._eastmoney_get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params,
            fallback_urls=[
                "https://82.push2his.eastmoney.com/api/qt/stock/kline/get",
                "https://27.push2his.eastmoney.com/api/qt/stock/kline/get",
            ],
        )
        klines = data.get("data", {}).get("klines") or []
        if not klines:
            raise DataSourceError("东方财富历史行情兜底接口未返回数据")

        rows = []
        for kline in klines:
            values = str(kline).split(",")
            if len(values) < 11:
                continue
            rows.append(
                {
                    "日期": values[0],
                    "开盘": values[1],
                    "收盘": values[2],
                    "最高": values[3],
                    "最低": values[4],
                    "成交量": values[5],
                    "成交额": values[6],
                    "振幅": values[7],
                    "涨跌幅": values[8],
                    "涨跌额": values[9],
                    "换手率": values[10],
                }
            )
        return pd.DataFrame(rows)

    def _get_history_tencent(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> pd.DataFrame:
        prefix = self._tencent_symbol(symbol)
        adjust_name = "qfq" if adjust == "qfq" else "hfq" if adjust == "hfq" else ""
        if adjust_name:
            param = f"{prefix},day,{self._date_dash(start_date)},{self._date_dash(end_date)},800,{adjust_name}"
            url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            key = f"{adjust_name}day"
        else:
            param = f"{prefix},day,{self._date_dash(start_date)},{self._date_dash(end_date)},800"
            url = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
            key = "day"

        data = self._http_get_json(url, {"param": param})
        symbol_payload = data.get("data", {}).get(prefix, {})
        klines = symbol_payload.get(key) or symbol_payload.get("day") or []
        if not klines:
            raise DataSourceError("腾讯历史行情兜底接口未返回数据")

        rows = []
        previous_close: float | None = None
        for values in klines:
            if len(values) < 6:
                continue
            trade_date, open_price, close, high, low, volume = values[:6]
            open_float = self._to_float(open_price)
            close_float = self._to_float(close)
            high_float = self._to_float(high)
            low_float = self._to_float(low)
            volume_float = self._to_float(volume)
            if close_float is None:
                continue

            base = previous_close or open_float or close_float
            change_amount = close_float - base
            change_percent = change_amount / base * 100 if base else None
            amplitude = (
                (high_float - low_float) / base * 100
                if high_float is not None and low_float is not None and base
                else None
            )
            rows.append(
                {
                    "日期": trade_date,
                    "开盘": open_float,
                    "收盘": close_float,
                    "最高": high_float,
                    "最低": low_float,
                    "成交量": volume_float,
                    "成交额": None,
                    "振幅": amplitude,
                    "涨跌幅": change_percent,
                    "涨跌额": change_amount,
                    "换手率": None,
                }
            )
            previous_close = close_float
        return pd.DataFrame(rows)

    def _eastmoney_get(
        self,
        url: str,
        params: dict[str, str],
        fallback_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        urls = [url, *(fallback_urls or [])]
        last_exc: requests.RequestException | None = None
        for current_url in urls:
            try:
                return self._http_get_json(current_url, params)
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning("Eastmoney direct request failed for %s: %s", current_url, exc)
        raise last_exc or DataSourceError("东方财富兜底接口请求失败")

    def _http_get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            url,
            params=params,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"},
        )
        response.raise_for_status()
        return response.json()

    def _http_get_text(self, url: str) -> str:
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"},
        )
        response.raise_for_status()
        return response.content.decode("gb18030", errors="replace")

    def _eastmoney_market_id(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return "1"
        return "0"

    def _eastmoney_adjust(self, adjust: str) -> str:
        if adjust == "qfq":
            return "1"
        if adjust == "hfq":
            return "2"
        return "0"

    def _eastmoney_scaled(self, value: object) -> float | None:
        number = self._to_float(value)
        if number is None or number == -1:
            return None
        return round(number / 100, 4)

    def _tencent_symbol(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return f"sh{symbol}"
        return f"sz{symbol}"

    def _date_dash(self, value: str) -> str:
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    def _parse_tencent_timestamp(self, value: str) -> str | None:
        try:
            parsed = datetime.strptime(value, "%Y%m%d%H%M%S")
        except ValueError:
            return None
        return parsed.replace(tzinfo=CHINA_TZ).isoformat()

    def _get_fixture_spot_records(self) -> list[dict[str, Any]]:
        fixtures = [
            ("000001", "平安银行(示例数据)", 12.65, 1.12),
            ("600519", "贵州茅台(示例数据)", 1688.80, -0.42),
            ("000858", "五粮液(示例数据)", 136.30, 0.86),
            ("300750", "宁德时代(示例数据)", 214.55, 2.18),
        ]
        records = []
        for symbol, name, price, change_percent in fixtures:
            previous_close = round(price / (1 + change_percent / 100), 2)
            records.append(
                {
                    "代码": symbol,
                    "名称": name,
                    "最新价": price,
                    "涨跌幅": change_percent,
                    "涨跌额": round(price - previous_close, 2),
                    "成交量": 1200000,
                    "成交额": round(price * 1200000, 2),
                    "振幅": 2.6,
                    "换手率": 1.35,
                    "最高": round(price * 1.012, 2),
                    "最低": round(price * 0.986, 2),
                    "今开": round(previous_close * 1.002, 2),
                    "昨收": previous_close,
                    "总市值": price * 1_000_000_000,
                    "流通市值": price * 700_000_000,
                }
            )
        return records

    def _get_fixture_history_frame(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        dates = pd.date_range(start=pd.to_datetime(start_date), end=pd.to_datetime(end_date), freq="B")
        if len(dates) == 0:
            dates = pd.date_range(end=pd.Timestamp.today(), periods=120, freq="B")

        base = 8 + (int(symbol[-2:]) % 30)
        rows = []
        previous_close = float(base)
        for index, trade_date in enumerate(dates):
            trend = index * 0.018
            wave = math.sin(index / 8) * 0.45
            close = max(1.0, base + trend + wave)
            open_price = previous_close * (1 + math.sin(index / 5) * 0.004)
            high = max(open_price, close) * 1.012
            low = min(open_price, close) * 0.988
            change_amount = close - previous_close
            change_percent = change_amount / previous_close * 100 if previous_close else 0
            volume = 800000 + (index % 20) * 18000
            rows.append(
                {
                    "日期": trade_date.strftime("%Y-%m-%d"),
                    "开盘": round(open_price, 2),
                    "收盘": round(close, 2),
                    "最高": round(high, 2),
                    "最低": round(low, 2),
                    "成交量": volume,
                    "成交额": round(volume * close, 2),
                    "振幅": round((high - low) / previous_close * 100, 2),
                    "涨跌幅": round(change_percent, 2),
                    "涨跌额": round(change_amount, 2),
                    "换手率": round(0.8 + (index % 12) * 0.07, 2),
                }
            )
            previous_close = close
        return pd.DataFrame(rows)

    def _normalize_history_frame(self, frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
        rename_map = {
            "日期": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "change_percent",
            "涨跌额": "change_amount",
            "换手率": "turnover_rate",
        }
        normalized = frame.rename(columns=rename_map).copy()
        normalized["symbol"] = symbol
        required_columns = [
            "symbol",
            "trade_date",
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
        for column in required_columns:
            if column not in normalized.columns:
                normalized[column] = None

        normalized = normalized[required_columns]
        normalized["trade_date"] = pd.to_datetime(normalized["trade_date"])
        for column in required_columns:
            if column not in {"symbol", "trade_date"}:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        normalized = normalized.sort_values("trade_date").reset_index(drop=True)
        return normalized

    def _serialize_frame(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        serializable = frame.copy()
        if "trade_date" in serializable.columns:
            serializable["trade_date"] = serializable["trade_date"].dt.strftime("%Y-%m-%d")
        return serializable.where(pd.notna(serializable), None).to_dict(orient="records")

    def _infer_market(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return "SH"
        if symbol.startswith(("0", "3")):
            return "SZ"
        if symbol.startswith(("4", "8", "9")):
            return "BJ"
        return "UNKNOWN"

    def _to_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_text(self, value: object) -> str | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        text = str(value).strip()
        return text or None
