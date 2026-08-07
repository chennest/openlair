<script setup lang="ts">
// 流水列表：按日分组（今天/昨天/日期）+ 日合计 + 分页
import { computed } from 'vue'
import Tag from '../../components/Tag.vue'
import type { Transaction } from './api'

const props = defineProps<{
  transactions: Transaction[]
  total: number
  page: number
  pageSize: number
  /** 是否共享账本（显示记账人） */
  shared?: boolean
}>()

const emit = defineEmits<{
  (e: 'remove', id: string): void
  (e: 'page', page: number): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

// ---------- 按日分组 ----------
interface DayGroup {
  label: string
  expense: number
  income: number
  rows: Transaction[]
}

const dayLabel = (d: string) => {
  const today = new Date()
  const t = (offset: number) => {
    const x = new Date(today)
    x.setDate(today.getDate() - offset)
    return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`
  }
  if (d === t(0)) return '今天'
  if (d === t(1)) return '昨天'
  return d
}

const groups = computed<DayGroup[]>(() => {
  const map = new Map<string, DayGroup>()
  for (const tr of props.transactions) {
    let g = map.get(tr.date)
    if (!g) {
      g = { label: dayLabel(tr.date), expense: 0, income: 0, rows: [] }
      map.set(tr.date, g)
    }
    g.rows.push(tr)
    if (tr.type === '收入') g.income += tr.amount
    else g.expense += tr.amount
  }
  return [...map.values()].map((g) => ({
    ...g,
    expense: Number(g.expense.toFixed(2)),
    income: Number(g.income.toFixed(2)),
  }))
})
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>历史流水</span>
      <Tag variant="gray">{{ total }} 条</Tag>
    </div>

    <div v-if="transactions.length === 0" class="empty">
      没有符合条件的记录，试试调整筛选条件。
    </div>

    <div v-for="g in groups" :key="g.label" class="day-group">
      <div class="day-head">
        <span class="day-label">{{ g.label }}</span>
        <span class="day-sum">
          <span v-if="g.income > 0" class="income num">+¥{{ g.income.toFixed(2) }}</span>
          <span v-if="g.expense > 0" class="expense num">-¥{{ g.expense.toFixed(2) }}</span>
        </span>
      </div>
      <div class="row-list">
        <div v-for="t in g.rows" :key="t.id" class="row">
          <span class="main">
            <span v-if="shared" class="face" :title="`${t.userName} 记的`" aria-hidden="true">{{ t.userName.slice(0, 1) }}</span>
            <span class="cat">{{ t.category }}</span>
            <span class="text">{{ t.note || '—' }}</span>
          </span>
          <span class="sub">
            <span class="amt num" :class="t.type === '收入' ? 'income' : 'expense'">
              {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
            </span>
            <button class="mini ghost" aria-label="删除" @click="emit('remove', t.id)">✕</button>
          </span>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <nav v-if="totalPages > 1" class="pager" aria-label="分页">
      <button class="page-btn" :disabled="page <= 1" @click="emit('page', page - 1)">‹ 上一页</button>
      <span class="page-info num">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="emit('page', page + 1)">下一页 ›</button>
    </nav>
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
.empty {
  padding: 28px 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.88rem;
}
.day-group + .day-group {
  margin-top: 22px;
}
.day-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin: 0 4px 6px;
}
.day-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.02em;
}
.day-sum {
  display: flex;
  gap: 10px;
  font-size: 11.5px;
  font-weight: 600;
}
.day-sum .income {
  color: var(--live);
}
.day-sum .expense {
  color: var(--text-3);
}
.row-list {
  display: flex;
  flex-direction: column;
  border-radius: var(--r-card);
  background: var(--hover);
  overflow: hidden;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
  background: var(--surface);
  transition: background 150ms ease;
}
.row:last-child {
  border-bottom: 0;
}
.row:hover {
  background: var(--hover);
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.cat {
  flex: 0 0 auto;
  padding: 2px 9px;
  border-radius: var(--r-pill);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.05);
}
.face {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--accent);
  flex: 0 0 auto;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-2);
}
.sub {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.amt {
  font-weight: 600;
}
.income {
  color: var(--live);
}
.expense {
  color: var(--text);
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
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 18px;
}
.page-btn {
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  background: var(--surface);
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease;
}
.page-btn:hover:not(:disabled) {
  border-color: var(--accent);
  background: rgba(0, 113, 227, 0.04);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--text-3);
}
</style>
