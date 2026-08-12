<script setup lang="ts">
// 总览模块页：本月支出 / 待办 / 日程 / 习惯 四卡聚合
import { computed, onMounted, ref } from 'vue'
import { overviewApi, type OverviewData } from './api'

const loading = ref(true)
const error = ref('')
const data = ref<OverviewData | null>(null)

/** 预算使用率（0–100，用于进度条） */
const budgetPercent = computed(() => {
  const amount = Number(data.value?.monthExpense.amount ?? 0)
  const budget = Number(data.value?.monthExpense.budget ?? 0)
  if (!budget) return 0
  return Math.min(100, Math.round((amount / budget) * 100))
})

onMounted(async () => {
  try {
    data.value = await overviewApi.get()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载总览…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p><small>请确认 mock server 已启用</small></div></div>

  <section v-else class="card-grid" aria-label="今日概览">
    <article class="card">
      <div class="card-title"><span>本月支出</span><span class="more">查看明细 →</span></div>
      <div class="big-num">¥{{ Number(data?.monthExpense.amount).toFixed(2) }}<small>预算 ¥{{ Number(data?.monthExpense.budget).toFixed(0) }}</small></div>
      <div class="budget-track" role="progressbar" :aria-valuenow="budgetPercent" aria-valuemin="0" aria-valuemax="100" aria-label="预算使用率">
        <div class="budget-fill" :style="{ width: budgetPercent + '%' }"></div>
      </div>
      <p class="hint">较上月同期 {{ Number(data?.monthExpense.trend) > 0 ? '↑' : '↓' }} {{ Math.abs(Number(data?.monthExpense.trend)) }}%</p>
    </article>

    <article class="card">
      <div class="card-title"><span>待办事项</span><span class="more">全部待办 →</span></div>
      <div class="row-list">
        <div v-for="item in data?.todos" :key="item.text" class="row">
          <span class="main text">{{ item.text }}</span>
          <span class="tag" :class="item.tagClass">{{ item.tag }}</span>
        </div>
      </div>
    </article>

    <article class="card">
      <div class="card-title"><span>今日日程</span><span class="more">查看日历 →</span></div>
      <div class="row-list">
        <div v-for="item in data?.upcoming" :key="item.text" class="row">
          <span class="main text">{{ item.text }}</span>
          <span class="sub">{{ item.date }}</span>
        </div>
      </div>
    </article>

    <article class="card">
      <div class="card-title"><span>习惯打卡</span><span class="more">全部习惯 →</span></div>
      <div class="row-list">
        <div v-for="item in data?.habits" :key="item.name" class="row">
          <span class="main text">{{ item.name }}</span>
          <span class="tag" :class="item.done ? 'green' : 'gray'">{{ item.done ? '已完成' : '待打卡' }}</span>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}
.card {
  padding: 22px 22px 20px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
  transition: transform 200ms var(--ease-out-quart), box-shadow 200ms var(--ease-out-quart);
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--sh-lift);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.more {
  color: var(--text-3);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 160ms ease;
}
.more:hover {
  color: var(--accent);
}
.big-num {
  font-size: 2.1rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.big-num small {
  margin-left: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0;
}
.budget-track {
  margin: 14px 0 0;
  height: 6px;
  border-radius: var(--r-pill);
  background: var(--track);
  overflow: hidden;
}
.budget-fill {
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--grad-blue);
  transition: width 400ms var(--ease-out-quart);
}
.hint {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 0.82rem;
  line-height: 1.6;
}
.row-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
}
.row:last-child {
  border-bottom: 0;
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub {
  color: var(--text-3);
  font-size: 0.78rem;
  white-space: nowrap;
}
.tag {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: var(--r-pill);
  font-size: 0.72rem;
  font-weight: 600;
}
.gold {
  color: #fff;
  background: var(--accent);
}
.green {
  color: #0a5a2c;
  background: rgba(48, 209, 88, 0.16);
}
.gray {
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.05);
}
.red {
  color: var(--heat);
  background: var(--heat-bg);
}
.placeholder {
  display: grid;
  place-items: center;
  min-height: 46vh;
  text-align: center;
  border: 1px dashed var(--faint);
  border-radius: var(--r-panel);
  background: var(--surface);
  color: var(--text-3);
}
.placeholder .symbol {
  font-size: 2.4rem;
  margin-bottom: 12px;
  color: var(--accent);
}
.placeholder small {
  color: var(--text-4);
}
</style>
