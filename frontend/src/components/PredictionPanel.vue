<template>
  <section class="panel prediction-panel">
    <div class="panel-header">
      <div>
        <span class="eyebrow">规则预测</span>
        <h2>趋势与风险</h2>
      </div>
      <el-tag :type="riskType" effect="dark" round>风险 {{ prediction.risk_level }}</el-tag>
    </div>

    <div class="probability-row">
      <div class="probability-item">
        <span>上涨概率</span>
        <strong class="up">{{ prediction.up_probability.toFixed(2) }}%</strong>
        <el-progress
          :percentage="prediction.up_probability"
          :stroke-width="8"
          color="#ef4444"
          :show-text="false"
        />
      </div>
      <div class="probability-item">
        <span>下跌概率</span>
        <strong class="down">{{ prediction.down_probability.toFixed(2) }}%</strong>
        <el-progress
          :percentage="prediction.down_probability"
          :stroke-width="8"
          color="#16a34a"
          :show-text="false"
        />
      </div>
    </div>

    <ul class="reason-list">
      <li v-for="reason in prediction.reasons" :key="reason">{{ reason }}</li>
    </ul>

    <div class="risk-notice">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ prediction.disclaimer }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import type { Prediction } from '../types/stock'

const props = defineProps<{
  prediction: Prediction
}>()

const riskType = computed(() => {
  if (props.prediction.risk_level === '高') return 'danger'
  if (props.prediction.risk_level === '中') return 'warning'
  return 'success'
})
</script>

