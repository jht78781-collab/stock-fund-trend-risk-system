<template>
  <main class="app-shell">
    <header class="topbar">
      <div class="brand-block">
        <h1>股票基金趋势分析与风险评估系统</h1>
        <span>股票分析 MVP</span>
      </div>
      <el-tag type="warning" effect="plain">仅供学习研究，不构成投资建议</el-tag>
    </header>

    <section class="toolbar">
      <el-autocomplete
        v-model="query"
        :fetch-suggestions="fetchSuggestions"
        value-key="label"
        clearable
        class="stock-search"
        placeholder="股票代码 / 名称"
        @select="handleSelect"
        @keyup.enter="loadAnalysis"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-autocomplete>
      <el-button type="primary" :icon="TrendCharts" :loading="loading" @click="loadAnalysis">
        分析
      </el-button>
      <el-button :icon="Refresh" :loading="loading" @click="refreshQuote">刷新行情</el-button>
      <el-tag v-if="wsConnected" type="success" effect="plain">WebSocket 已连接</el-tag>
      <el-tag v-else type="info" effect="plain">WebSocket 未连接</el-tag>
    </section>

    <section v-if="analysis" class="summary-grid">
      <div class="price-panel panel">
        <div class="quote-title">
          <div>
            <h2>{{ analysis.quote.name || analysis.basic_info.name || analysis.quote.symbol }}</h2>
            <span>{{ analysis.quote.symbol }} · {{ analysis.basic_info.market || 'A股' }}</span>
          </div>
          <el-tag>{{ analysis.basic_info.industry || '未分类' }}</el-tag>
        </div>
        <div class="price-row">
          <strong :class="changeClass">{{ formatNumber(analysis.quote.price, 2) }}</strong>
          <span :class="changeClass">
            {{ formatSigned(analysis.quote.change_percent, 2) }}%
          </span>
          <span :class="changeClass">{{ formatSigned(analysis.quote.change_amount, 2) }}</span>
        </div>
        <div class="quote-meta">
          <span>开 {{ formatNumber(analysis.quote.open, 2) }}</span>
          <span>高 {{ formatNumber(analysis.quote.high, 2) }}</span>
          <span>低 {{ formatNumber(analysis.quote.low, 2) }}</span>
          <span>昨 {{ formatNumber(analysis.quote.previous_close, 2) }}</span>
          <span>换手 {{ formatNumber(analysis.quote.turnover_rate, 2) }}%</span>
        </div>
      </div>

      <div class="indicator-panel panel">
        <div class="panel-header compact">
          <h2>技术指标</h2>
          <span>{{ latestDate }}</span>
        </div>
        <div class="indicator-grid">
          <div v-for="item in indicatorItems" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section v-if="analysis" class="content-grid">
      <section class="panel chart-panel">
        <div class="panel-header">
          <div>
            <span class="eyebrow">K 线</span>
            <h2>价格、均线、成交量与 MACD</h2>
          </div>
          <span class="timestamp">{{ analysis.quote.source || '行情源' }} · {{ quoteTime }}</span>
        </div>
        <KLineChart :history="analysis.history" />
      </section>

      <PredictionPanel :prediction="analysis.prediction" />
    </section>

    <el-empty v-else-if="!loading" description="暂无数据" />
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search, TrendCharts } from '@element-plus/icons-vue'
import KLineChart from '../components/KLineChart.vue'
import PredictionPanel from '../components/PredictionPanel.vue'
import {
  getStockAnalysis,
  getStockQuote,
  searchStocks,
  stockWebSocketUrl
} from '../api/stock'
import type { StockAnalysis, StockQuote, StockSearchItem } from '../types/stock'

interface Suggestion extends StockSearchItem {
  label: string
  value: string
}

const query = ref('000001')
const analysis = ref<StockAnalysis | null>(null)
const loading = ref(false)
const wsConnected = ref(false)
let socket: WebSocket | null = null

const currentSymbol = computed(() => {
  const source = analysis.value?.quote.symbol || query.value
  const match = source.match(/\d{6}/)
  return match ? match[0] : source
})

const changeClass = computed(() => {
  const change = analysis.value?.quote.change_percent ?? 0
  if (change > 0) return 'is-up'
  if (change < 0) return 'is-down'
  return 'is-flat'
})

const latestDate = computed(() => {
  const history = analysis.value?.history ?? []
  return history.length ? history[history.length - 1].trade_date : '-'
})

const quoteTime = computed(() => {
  const time = analysis.value?.quote.source_timestamp || analysis.value?.quote.timestamp
  if (!time) return '-'
  return new Date(time).toLocaleString()
})

const indicatorItems = computed(() => {
  const latest = analysis.value?.latest_indicators
  return [
    { label: 'MA5', value: formatNumber(latest?.ma5, 2) },
    { label: 'MA10', value: formatNumber(latest?.ma10, 2) },
    { label: 'MA20', value: formatNumber(latest?.ma20, 2) },
    { label: 'MACD', value: formatNumber(latest?.macd, 4) },
    { label: 'Signal', value: formatNumber(latest?.macd_signal, 4) },
    { label: 'RSI', value: formatNumber(latest?.rsi, 2) }
  ]
})

async function fetchSuggestions(keyword: string, cb: (items: Suggestion[]) => void) {
  if (!keyword.trim()) {
    cb([])
    return
  }
  try {
    const results = await searchStocks(keyword, 10)
    cb(
      results.map((item) => ({
        ...item,
        label: `${item.symbol} ${item.name || ''}`,
        value: item.symbol
      }))
    )
  } catch {
    cb([])
  }
}

function handleSelect(item: Suggestion) {
  query.value = item.symbol
  loadAnalysis()
}

async function loadAnalysis() {
  const symbol = extractSymbol(query.value)
  if (!symbol) {
    ElMessage.warning('请输入 6 位股票代码')
    return
  }

  loading.value = true
  try {
    analysis.value = await getStockAnalysis(symbol)
    query.value = analysis.value.quote.symbol
    connectWebSocket(analysis.value.quote.symbol)
  } catch (error) {
    ElMessage.error(readError(error))
  } finally {
    loading.value = false
  }
}

async function refreshQuote() {
  if (!analysis.value) {
    await loadAnalysis()
    return
  }
  try {
    const quote = await getStockQuote(currentSymbol.value)
    applyQuote(quote)
  } catch (error) {
    ElMessage.error(readError(error))
  }
}

function connectWebSocket(symbol: string) {
  socket?.close()
  socket = new WebSocket(stockWebSocketUrl(symbol))
  socket.onopen = () => {
    wsConnected.value = true
  }
  socket.onclose = () => {
    wsConnected.value = false
  }
  socket.onerror = () => {
    wsConnected.value = false
  }
  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data)
    if (payload.type === 'quote') {
      applyQuote(payload.data)
    }
  }
}

function applyQuote(quote: StockQuote) {
  if (!analysis.value) return
  analysis.value = {
    ...analysis.value,
    quote
  }
}

function extractSymbol(value: string): string {
  return value.match(/\d{6}/)?.[0] ?? ''
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })
}

function formatSigned(value: number | null | undefined, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNumber(value, digits)}`
}

function readError(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
    if (detail) return detail
  }
  return '请求失败'
}

onMounted(() => {
  loadAnalysis()
})

onBeforeUnmount(() => {
  socket?.close()
})
</script>
