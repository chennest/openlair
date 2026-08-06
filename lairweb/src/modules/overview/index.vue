<script setup lang="ts">
// 总揽模块页：本月支出 / 待办 / 日程 / 习惯 四卡聚合
import { onMounted, ref } from 'vue'
import { overviewApi, type OverviewData } from './api'

const loading = ref(true)
const error = ref('')
const data = ref<OverviewData | null>(null)

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
  <div v-if="loading" class="placeholder"><div><p>正在加载总揽…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p><small>请确认 mock server 已启用</small></div></div>

  <section v-else class="card-grid" aria-label="今日概览">
    <article class="card">
      <div class="card-title"><span>本月支出</span><span class="more">查看明细 →</span></div>
      <div class="big-num">¥{{ Number(data?.monthExpense.amount).toFixed(2) }}<small>预算 ¥{{ Number(data?.monthExpense.budget).toFixed(0) }}</small></div>
      <p class="hint">较上月同期 {{ Number(data?.monthExpense.trend) > 0 ? '↑' : '↓' }} {{ Math.abs(Number(data?.monthExpense.trend)) }}%，餐饮与交通是主要支出项。</p>
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
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.66);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: rgba(242, 234, 223, 0.72);
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}
.more {
  color: rgba(242, 234, 223, 0.4);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: none;
  letter-spacing: 0;
  cursor: pointer;
}
.more:hover {
  color: #f6d37a;
}
.big-num {
  font-size: 2.1rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #f6d37a;
}
.big-num small {
  margin-left: 6px;
  font-size: 0.9rem;
  font-weight: 700;
  color: rgba(242, 234, 223, 0.5);
  letter-spacing: 0;
}
.hint {
  margin: 6px 0 0;
  color: rgba(242, 234, 223, 0.5);
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
  border-bottom: 1px solid rgba(242, 234, 223, 0.06);
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
  color: rgba(242, 234, 223, 0.45);
  font-size: 0.78rem;
  white-space: nowrap;
}
.tag {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
}
.gold {
  color: #14120f;
  background: #f6d37a;
}
.green {
  color: #0e1f16;
  background: #8ee6a5;
}
.gray {
  color: rgba(242, 234, 223, 0.7);
  background: rgba(255, 255, 255, 0.08);
}
.red {
  color: #ffd9c9;
  background: rgba(204, 93, 43, 0.28);
}
.placeholder {
  display: grid;
  place-items: center;
  min-height: 46vh;
  text-align: center;
  border: 1px dashed rgba(242, 234, 223, 0.16);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.4);
  color: rgba(242, 234, 223, 0.48);
}
.placeholder .symbol {
  font-size: 2.4rem;
  margin-bottom: 12px;
  color: rgba(246, 211, 122, 0.7);
}
.placeholder small {
  color: rgba(242, 234, 223, 0.38);
}
</style>
