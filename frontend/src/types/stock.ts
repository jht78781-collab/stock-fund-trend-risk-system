export interface StockSearchItem {
  symbol: string
  name?: string | null
  price?: number | null
  change_percent?: number | null
}

export interface StockBasicInfo {
  symbol: string
  name?: string | null
  market?: string | null
  industry?: string | null
  listed_date?: string | null
  total_share?: number | null
  float_share?: number | null
  total_market_value?: number | null
  float_market_value?: number | null
}

export interface StockQuote {
  symbol: string
  name?: string | null
  price?: number | null
  change_percent?: number | null
  change_amount?: number | null
  volume?: number | null
  amount?: number | null
  high?: number | null
  low?: number | null
  open?: number | null
  previous_close?: number | null
  turnover_rate?: number | null
  source?: string | null
  source_timestamp?: string | null
  timestamp: string
}

export interface KLineItem {
  trade_date: string
  open?: number | null
  close?: number | null
  high?: number | null
  low?: number | null
  volume?: number | null
  amount?: number | null
  amplitude?: number | null
  change_percent?: number | null
  change_amount?: number | null
  turnover_rate?: number | null
  ma5?: number | null
  ma10?: number | null
  ma20?: number | null
  macd?: number | null
  macd_signal?: number | null
  macd_hist?: number | null
  rsi?: number | null
}

export interface LatestIndicators {
  ma5?: number | null
  ma10?: number | null
  ma20?: number | null
  macd?: number | null
  macd_signal?: number | null
  macd_hist?: number | null
  rsi?: number | null
}

export interface Prediction {
  symbol: string
  close_price?: number | null
  up_probability: number
  down_probability: number
  risk_level: '低' | '中' | '高' | string
  reasons: string[]
  disclaimer: string
  generated_at: string
}

export interface StockAnalysis {
  basic_info: StockBasicInfo
  quote: StockQuote
  latest_indicators: LatestIndicators
  prediction: Prediction
  history: KLineItem[]
}

export interface StockPredictionRecord extends Omit<Prediction, 'generated_at'> {
  id: number
  created_at: string
}
