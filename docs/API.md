# 接口文档

服务默认地址：`http://127.0.0.1:8000`

交互式 OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 健康检查

`GET /health`

返回：

```json
{"status": "ok"}
```

## 股票搜索

`GET /api/v1/stocks/search?keyword=000001&limit=20`

参数：

- `keyword`：股票代码或名称关键字，必填。
- `limit`：返回条数，默认 `20`，最大 `100`。

## 实时行情

`GET /api/v1/stocks/{symbol}/quote`

示例：

`GET /api/v1/stocks/000001/quote`

返回核心字段：

- `price`：当前价格。
- `change_percent`：涨跌幅。
- `change_amount`：涨跌额。
- `volume`：成交量。
- `amount`：成交额。
- `source`：实际行情来源，例如 `Eastmoney`、`Tencent`、`AKShare`。
- `source_timestamp`：行情源返回的行情时间；如果为空，表示上游未提供明确时间。
- `timestamp`：行情查询时间。

说明：WebSocket 和实时行情接口会按配置周期重新请求后端，但价格是否变化取决于上游行情源是否刷新。非交易时段通常返回最近一个交易日收盘后的快照。

## 历史 K 线和技术指标

`GET /api/v1/stocks/{symbol}/history?start_date=2025-01-01&end_date=2026-06-19&adjust=qfq`

参数：

- `start_date`：开始日期，支持 `YYYY-MM-DD` 或 `YYYYMMDD`，默认近 1 年。
- `end_date`：结束日期，默认今天。
- `adjust`：复权方式，`qfq` 前复权、`hfq` 后复权、空字符串不复权。

返回每个交易日的 OHLCV、涨跌幅、换手率、`MA5`、`MA10`、`MA20`、`MACD`、`MACD signal`、`MACD hist`、`RSI`。

## 趋势分析与风险评估

`GET /api/v1/stocks/{symbol}/analysis?start_date=2025-01-01&adjust=qfq`

返回：

- `basic_info`：股票基础信息。
- `quote`：实时行情。
- `latest_indicators`：最近交易日技术指标。
- `prediction`：简单规则模型输出。
- `history`：历史 K 线和技术指标。

`prediction` 固定包含：

- `up_probability`：上涨概率。
- `down_probability`：下跌概率。
- `risk_level`：风险等级，取值为 `低`、`中`、`高`。
- `reasons`：预测理由。
- `disclaimer`：`仅供学习研究，不构成投资建议。`

## 预测记录

`GET /api/v1/stocks/{symbol}/predictions?limit=20`

返回 MySQL 中保存的历史预测记录。

## WebSocket 行情推送

`WS /api/v1/ws/stocks/{symbol}`

示例：

`ws://127.0.0.1:8000/api/v1/ws/stocks/000001`

服务端每 5 秒推送一次：

```json
{
  "type": "quote",
  "data": {
    "symbol": "000001",
    "name": "平安银行",
    "price": 10.12,
    "change_percent": 1.2,
    "source": "Tencent",
    "source_timestamp": "2026-06-18T16:14:45+08:00",
    "timestamp": "2026-06-19T10:00:00+08:00"
  },
  "risk_notice": "仅供学习研究，不构成投资建议。"
}
```
