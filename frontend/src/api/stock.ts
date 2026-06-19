import axios from 'axios'
import type {
  StockAnalysis,
  StockPredictionRecord,
  StockQuote,
  StockSearchItem
} from '../types/stock'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000
})

export async function searchStocks(keyword: string, limit = 20): Promise<StockSearchItem[]> {
  const { data } = await api.get<StockSearchItem[]>('/stocks/search', {
    params: { keyword, limit }
  })
  return data
}

export async function getStockQuote(symbol: string): Promise<StockQuote> {
  const { data } = await api.get<StockQuote>(`/stocks/${symbol}/quote`)
  return data
}

export async function getStockAnalysis(symbol: string): Promise<StockAnalysis> {
  const { data } = await api.get<StockAnalysis>(`/stocks/${symbol}/analysis`)
  return data
}

export async function getPredictionRecords(
  symbol: string,
  limit = 20
): Promise<StockPredictionRecord[]> {
  const { data } = await api.get<StockPredictionRecord[]>(`/stocks/${symbol}/predictions`, {
    params: { limit }
  })
  return data
}

export function stockWebSocketUrl(symbol: string): string {
  const configured = import.meta.env.VITE_WS_BASE_URL
  if (configured) {
    return `${configured.replace(/\/$/, '')}/stocks/${symbol}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1/ws/stocks/${symbol}`
}

