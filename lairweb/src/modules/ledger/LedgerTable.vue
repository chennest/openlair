<script setup lang="ts">
// 流水表格（纯展示 + 删除）
import Tag from '../../components/Tag.vue'
import type { Transaction } from './api'

defineProps<{ transactions: Transaction[] }>()

const emit = defineEmits<{
  (e: 'remove', id: string): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>最近流水</span>
      <Tag variant="gray">{{ transactions.length }} 条</Tag>
    </div>
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>日期</th><th>分类</th><th>备注</th><th>类型</th><th class="num">金额</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in transactions" :key="t.id">
            <td class="sub">{{ t.date }}</td>
            <td>{{ t.category }}</td>
            <td class="sub">{{ t.note }}</td>
            <td><Tag :variant="t.type === '收入' ? 'green' : 'gray'">{{ t.type }}</Tag></td>
            <td class="num" :class="t.type === '收入' ? 'income' : 'expense'">
              {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
            </td>
            <td class="num"><button class="mini ghost" @click="emit('remove', t.id)">✕</button></td>
          </tr>
        </tbody>
      </table>
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
.table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.table th,
.table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--hairline);
}
.table th {
  color: var(--text-3);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.06em;
}
.table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.table .income {
  color: var(--live);
}
.table .expense {
  color: var(--heat);
}
.sub {
  color: var(--text-3);
  font-size: 0.78rem;
}
.mini.ghost {
  min-width: 0;
  padding: 3px 8px;
  border: 0;
  border-radius: 8px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  transition: color 160ms ease;
}
.mini.ghost:hover {
  color: var(--heat);
}
</style>
