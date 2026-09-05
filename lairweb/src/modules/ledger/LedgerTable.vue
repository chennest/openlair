<script setup lang="ts">
// 流水列表：按日分组（今天/昨天/日期）+ 日合计 + 分页
import { computed } from 'vue'
import { ChevronLeft, ChevronRight, X } from '@lucide/vue'
import Tag from '../../components/Tag.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
  (e: 'remove', id: number): void
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

    <!-- 工具行：筛选/搜索由父组件通过 slot 注入（流水为主体，筛选归位于卡片头部） -->
    <slot name="toolbar"></slot>

    <!-- 表头：与行使用同一套栅格列，形成对齐的表格观感 -->
    <div v-if="transactions.length > 0" class="thead" :class="{ shared }" aria-hidden="true">
      <span>分类</span>
      <span>备注</span>
      <span v-if="shared">记账人</span>
      <span class="ta-r">金额</span>
      <span></span>
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
      <div class="row-list" :class="{ shared }">
        <div v-for="t in g.rows" :key="t.id" class="row">
          <span class="cat">
            <Badge variant="secondary" class="flex-none text-[0.72rem] font-semibold text-[var(--text-2)]!">{{ t.category }}</Badge>
          </span>
          <span class="text" :title="t.note || ''">{{ t.note || '—' }}</span>
          <span v-if="shared" class="user" :title="`${t.userName} 记的`">
            <span class="face" aria-hidden="true">{{ t.userName.slice(0, 1) }}</span>
            {{ t.userName }}
          </span>
          <span class="amt num" :class="t.type === '收入' ? 'income' : 'expense'">
            {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
          </span>
          <span class="op">
            <Button variant="ghost" size="icon-sm" class="text-[var(--text-3)] hover:text-[var(--heat)]! hover:bg-transparent" aria-label="删除" @click="emit('remove', t.id)">
              <X class="size-3.5" />
            </Button>
          </span>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <nav v-if="totalPages > 1" class="pager" aria-label="分页">
      <Button variant="outline" size="sm" class="rounded-full! pl-4 pr-4 py-[7px] text-[13px] font-semibold text-foreground bg-white cursor-pointer hover:border-primary hover:bg-primary/4 disabled:opacity-[0.4]" :disabled="page <= 1" @click="emit('page', page - 1)">
        <ChevronLeft class="size-4" />
        上一页
      </Button>
      <span class="page-info num">{{ page }} / {{ totalPages }}</span>
      <Button variant="outline" size="sm" class="rounded-full! pl-4 pr-4 py-[7px] text-[13px] font-semibold text-foreground bg-white cursor-pointer hover:border-primary hover:bg-primary/4 disabled:opacity-[0.4]" :disabled="page >= totalPages" @click="emit('page', page + 1)">
        下一页
        <ChevronRight class="size-4" />
      </Button>
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
/* 表格栅格：分类 | 备注 | (记账人) | 金额 | 操作；表头与行共用同一套列 */
.thead,
.row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 120px 36px;
  align-items: center;
  gap: 12px;
}
.thead.shared,
.row-list.shared .row {
  grid-template-columns: 92px minmax(0, 1fr) 96px 120px 36px;
}
.thead {
  padding: 0 14px 8px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.02em;
}
.thead .ta-r {
  text-align: right;
}
.row {
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
.cat {
  display: flex;
  min-width: 0;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-2);
}
.user {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--text-3);
  overflow: hidden;
  white-space: nowrap;
}
.face {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--accent);
  flex: 0 0 auto;
}
.amt {
  font-weight: 600;
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.op {
  display: flex;
  justify-content: flex-end;
}
.income {
  color: var(--live);
}
.expense {
  color: var(--text);
}
@media (max-width: 680px) {
  .thead {
    display: none;
  }
  .thead.shared,
  .row-list.shared .row {
    grid-template-columns: 84px minmax(0, 1fr) 110px 32px;
  }
  .row-list.shared .row .user {
    display: none;
  }
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 18px;
}
.page-info {
  font-size: 13px;
  color: var(--text-3);
}
</style>
