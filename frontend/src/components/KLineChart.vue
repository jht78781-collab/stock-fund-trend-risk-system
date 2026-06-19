<template>
  <div ref="chartRef" class="kline-chart" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { KLineItem } from '../types/stock'

const props = defineProps<{
  history: KLineItem[]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function n(value: number | null | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const dates = props.history.map((item) => item.trade_date)
  const candles = props.history.map((item) => [
    n(item.open),
    n(item.close),
    n(item.low),
    n(item.high)
  ])
  const volumes = props.history.map((item) => n(item.volume))
  const ma5 = props.history.map((item) => item.ma5 ?? null)
  const ma10 = props.history.map((item) => item.ma10 ?? null)
  const ma20 = props.history.map((item) => item.ma20 ?? null)
  const macd = props.history.map((item) => item.macd ?? null)
  const macdSignal = props.history.map((item) => item.macd_signal ?? null)
  const macdHist = props.history.map((item) => item.macd_hist ?? null)

  chart.setOption({
    animation: false,
    color: ['#2563eb', '#16a34a', '#f59e0b'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      top: 8,
      data: ['K线', 'MA5', 'MA10', 'MA20', '成交量', 'MACD', 'Signal']
    },
    axisPointer: {
      link: [{ xAxisIndex: [0, 1, 2] }]
    },
    grid: [
      { left: 52, right: 24, top: 48, height: '52%' },
      { left: 52, right: 24, top: '66%', height: '12%' },
      { left: 52, right: 24, top: '82%', height: '11%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#9ca3af' } },
        axisLabel: { show: false }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: '#d1d5db' } }
      },
      {
        type: 'category',
        gridIndex: 2,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#d1d5db' } }
      }
    ],
    yAxis: [
      { scale: true, axisLine: { show: true }, splitLine: { lineStyle: { color: '#edf0f5' } } },
      {
        scale: true,
        gridIndex: 1,
        axisLabel: { formatter: '{value}' },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 2,
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2], start: 55, end: 100 },
      { show: true, xAxisIndex: [0, 1, 2], type: 'slider', bottom: 6, height: 18, start: 55, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: candles,
        itemStyle: {
          color: '#ef4444',
          color0: '#16a34a',
          borderColor: '#ef4444',
          borderColor0: '#16a34a'
        }
      },
      { name: 'MA5', type: 'line', data: ma5, smooth: true, showSymbol: false, lineStyle: { width: 1.4 } },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, showSymbol: false, lineStyle: { width: 1.4 } },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, showSymbol: false, lineStyle: { width: 1.4 } },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: { color: '#94a3b8' }
      },
      {
        name: 'MACD',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdHist,
        itemStyle: {
          color: (params: { value: number }) => (params.value >= 0 ? '#ef4444' : '#16a34a')
        }
      },
      {
        name: 'Signal',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdSignal,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#64748b' }
      },
      {
        name: 'MACD线',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macd,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#2563eb' }
      }
    ]
  })
}

onMounted(() => {
  renderChart()
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartRef.value)
  }
})

watch(
  () => props.history,
  () => renderChart(),
  { deep: true }
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

