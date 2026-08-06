<script setup lang="ts">
// 收支摘要三卡（纯展示）
import type { LedgerSummary } from './api'

defineProps<{ summary: LedgerSummary }>()
</script>

<template>
  <section class="card-grid" aria-label="收支摘要">
    <article class="card">
      <div class="card-title"><span>本月收入</span></div>
      <div class="big-num">¥{{ Number(summary.income).toFixed(2) }}</div>
    </article>
    <article class="card">
      <div class="card-title"><span>本月支出</span></div>
      <div class="big-num expense">¥{{ Number(summary.expense).toFixed(2) }}</div>
    </article>
    <article class="card">
      <div class="card-title"><span>结余</span></div>
      <div class="big-num">¥{{ Number(summary.balance).toFixed(2) }}</div>
    </article>
  </section>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
}
.card {
  padding: 22px 22px 20px;
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.66);
}
.card-title {
  margin-bottom: 16px;
  color: rgba(242, 234, 223, 0.72);
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}
.big-num {
  font-size: 2.1rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #f6d37a;
}
.expense {
  color: #ffac8b;
}
</style>
