<script setup lang="ts">
// 近 6 月收支趋势：CSS 双柱（支出 = 灰度柱，收入 = live 柱），无图表库依赖
import { computed } from 'vue'
import type { TrendPoint } from './api'

const props = defineProps<{ trend: TrendPoint[] }>()

const max = computed(() => {
  let m = 0
  for (const p of props.trend) m = Math.max(m, p.expense, p.income)
  return m || 1
})

const monthLabel = (m: string) => {
  const [, mm] = m.split('-')
  return `${Number(mm)}月`
}
</script>

<template>
  <article class="card">
    <div class="card-title"><span>近 6 月收支</span></div>
    <div v-if="trend.length === 0" class="empty">暂无趋势数据</div>
    <div class="bars">
      <div v-for="p in trend" :key="p.month" class="bar-col">
        <div class="pair">
          <div class="track">
            <i class="inc" :style="{ height: (p.income / max) * 100 + '%' }" :title="`收入 ¥${p.income.toFixed(2)}`"></i>
          </div>
          <div class="track">
            <i class="exp" :style="{ height: (p.expense / max) * 100 + '%' }" :title="`支出 ¥${p.expense.toFixed(2)}`"></i>
          </div>
        </div>
        <span class="label">{{ monthLabel(p.month) }}</span>
      </div>
    </div>
    <div class="legend">
      <span><i class="dot inc-dot"></i>收入</span>
      <span><i class="dot exp-dot"></i>支出</span>
    </div>
  </article>
</template>

<style scoped>
.card {
  padding: 22px 22px 20px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.card-title {
  margin-bottom: 18px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.empty {
  padding: 20px 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.84rem;
}
.bars {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  height: 130px;
}
.bar-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  height: 100%;
}
.pair {
  flex: 1;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 5px;
  min-height: 0;
}
.track {
  width: 12px;
  max-width: 16px;
  height: 100%;
  display: flex;
  align-items: flex-end;
  border-radius: 4px;
  background: transparent;
}
.track i {
  display: block;
  width: 100%;
  border-radius: 4px;
  transition: height 500ms var(--ease-out-quart);
}
.inc {
  background: var(--live);
  opacity: 0.85;
}
.exp {
  background: var(--text);
  opacity: 0.75;
}
.label {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--text-3);
  white-space: nowrap;
}
.legend {
  display: flex;
  justify-content: center;
  gap: 18px;
  margin-top: 14px;
  font-size: 11.5px;
  color: var(--text-3);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 3px;
}
.inc-dot {
  background: var(--live);
}
.exp-dot {
  background: var(--text);
}
</style>
