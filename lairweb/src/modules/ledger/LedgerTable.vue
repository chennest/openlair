<script setup lang="ts">
// 流水表格：shadcn Table + 完整分页器（每页条数 / 共 N 条 / 页码 / 上下页）
// 纯展示：props 进，交互 emit 出（remove / page / page-size）
import { computed } from 'vue'
import { ChevronLeft, ChevronRight, Pencil, X } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Transaction } from './api'

const props = defineProps<{
  transactions: Transaction[]
  total: number
  page: number
  pageSize: number
  /** 是否共享账本（显示记账人列） */
  shared?: boolean
}>()

const emit = defineEmits<{
  (e: 'remove', id: number): void
  (e: 'edit', tx: Transaction): void
  (e: 'page', page: number): void
  (e: 'page-size', size: number): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const rangeText = computed(() => {
  if (props.total === 0) return '共 0 条'
  const start = (props.page - 1) * props.pageSize + 1
  const end = Math.min(props.page * props.pageSize, props.total)
  return `共 ${props.total} 条 · 第 ${start}-${end} 条`
})

const PAGE_SIZES = [10, 20, 50]
const sizeKey = computed({
  get: () => String(props.pageSize),
  set: (v: string) => emit('page-size', Number(v)),
})

const fmtDate = (iso: string) => {
  // YYYY-MM-DD → MM-DD（跨年时显示完整年份）
  const [, m, d] = iso.split('-')
  return iso.slice(0, 4) === String(new Date().getFullYear()) ? `${m}-${d}` : iso
}
</script>

<template>
  <section class="panel">
    <div class="panel-head">
      <span class="panel-title">历史流水</span>
      <span class="range num">{{ rangeText }}</span>
    </div>

    <!-- 工具行：筛选/搜索由父组件通过 slot 注入 -->
    <div class="panel-toolbar">
      <slot name="toolbar"></slot>
    </div>

    <Table class="desk-table">
      <TableHeader>
        <TableRow class="hover:bg-transparent! border-b-[var(--hairline)]!">
          <TableHead class="h-11 w-[96px] pl-5 text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!">日期</TableHead>
          <TableHead class="h-11 w-[104px] text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!">分类</TableHead>
          <TableHead class="h-11 text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!">备注</TableHead>
          <TableHead class="h-11 w-[128px] text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!">记账人</TableHead>
          <TableHead class="h-11 w-[140px] pr-5 text-right text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!">金额</TableHead>
          <TableHead class="h-11 w-[96px] pr-5 text-right text-[11.5px] font-semibold tracking-[0.02em] text-[var(--text-3)]!"><span class="sr-only">操作</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody class="[&_tr:last-child]:border-b-0">
        <TableEmpty v-if="transactions.length === 0" :colspan="6">
          没有符合条件的记录，试试调整筛选条件。
        </TableEmpty>
        <TableRow v-for="t in transactions" :key="t.id" class="h-[52px] border-b-[var(--hairline)]! hover:bg-[var(--hover)]!">
          <TableCell class="pl-5 text-[0.82rem] tabular-nums text-[var(--text-3)]">{{ fmtDate(t.date) }}</TableCell>
          <TableCell>
            <Badge variant="secondary" class="text-[0.72rem] font-semibold text-[var(--text-2)]!">{{ t.category }}</Badge>
          </TableCell>
          <TableCell class="max-w-0">
            <span class="block truncate text-[var(--text-2)]" :title="t.note || ''">{{ t.note || '—' }}</span>
          </TableCell>
          <TableCell>
            <span class="inline-flex items-center gap-1.5 text-[0.82rem] text-[var(--text-3)]" :title="`由 ${t.userName} 记录`">
              <span class="face" aria-hidden="true">{{ (t.userName || '?').slice(0, 1) }}</span>
              {{ t.userName || '未知' }}
            </span>
          </TableCell>
          <TableCell
            class="pr-5 text-right font-semibold tabular-nums"
            :class="t.type === '收入' ? 'text-[var(--live)]' : 'text-[var(--text)]'"
          >
            {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
          </TableCell>
          <TableCell class="pr-5 text-right">
            <span class="inline-flex items-center justify-end gap-0.5">
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-[var(--text-3)] hover:text-[var(--accent)]! hover:bg-transparent"
                aria-label="编辑"
                @click="emit('edit', t)"
              >
                <Pencil class="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-[var(--text-3)] hover:text-[var(--heat)]! hover:bg-transparent"
                aria-label="删除"
                @click="emit('remove', t.id)"
              >
                <X class="size-3.5" />
              </Button>
            </span>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <!-- 移动端列表：手机壳布局（≤860px）下替代 6 列表格，单面板 + hairline 分行 -->
    <ul class="m-list">
      <li v-if="transactions.length === 0" class="m-empty">没有符合条件的记录，试试调整筛选条件。</li>
      <li v-for="t in transactions" :key="t.id" class="m-row">
        <div class="m-row-top">
          <Badge variant="secondary" class="m-cat text-[0.72rem] font-semibold text-[var(--text-2)]!">{{ t.category }}</Badge>
          <span class="m-note" :title="t.note || ''">{{ t.note || '—' }}</span>
          <span class="m-amt num" :class="t.type === '收入' ? 'is-income' : ''">
            {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
          </span>
        </div>
        <div class="m-row-sub">
          <span class="m-meta">
            <span class="face" aria-hidden="true">{{ (t.userName || '?').slice(0, 1) }}</span>
            <span class="num">{{ fmtDate(t.date) }}</span>
            <span>·</span>
            <span>{{ t.userName || '未知' }}</span>
          </span>
          <span class="m-acts">
            <button type="button" class="m-act is-edit" aria-label="编辑" @click="emit('edit', t)">
              <Pencil class="size-4" />
            </button>
            <button type="button" class="m-act is-del" aria-label="删除" @click="emit('remove', t.id)">
              <X class="size-4" />
            </button>
          </span>
        </div>
      </li>
    </ul>

    <!-- 分页器 -->
    <nav v-if="total > 0" class="pager" aria-label="分页">      <div class="pager-left">
        <span class="per">每页</span>
        <Select v-model="sizeKey">
          <SelectTrigger class="size-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="s in PAGE_SIZES" :key="s" :value="String(s)">{{ s }}</SelectItem>
          </SelectContent>
        </Select>
        <span class="per">条</span>
      </div>
      <div class="pager-right">
        <Button
          variant="outline"
          size="sm"
          class="rounded-full! px-4 py-[7px] text-[13px] font-semibold bg-white cursor-pointer hover:border-primary hover:bg-primary/4 disabled:opacity-[0.4]"
          :disabled="page <= 1"
          @click="emit('page', page - 1)"
        >
          <ChevronLeft class="size-4" />
          上一页
        </Button>
        <span class="page-info num">{{ page }} / {{ totalPages }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-full! px-4 py-[7px] text-[13px] font-semibold bg-white cursor-pointer hover:border-primary hover:bg-primary/4 disabled:opacity-[0.4]"
          :disabled="page >= totalPages"
          @click="emit('page', page + 1)"
        >
          下一页
          <ChevronRight class="size-4" />
        </Button>
      </div>
    </nav>
  </section>
</template>

<style scoped>
.panel {
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 0;
}
.panel-title {
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.range {
  font-size: 12px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.panel-toolbar {
  padding: 12px 20px 4px;
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
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 20px 16px;
  border-top: 1px solid var(--hairline);
}
.pager-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.per {
  font-size: 12.5px;
  color: var(--text-3);
}
.size-select {
  height: 32px;
  width: 76px;
  border-radius: var(--r-pill);
  font-size: 13px;
}
.pager-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-info {
  font-size: 13px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

/* ---------- 移动端列表（≤860px 手机壳布局） ---------- */
/* 桌面：只显示表格 */
.m-list {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0 0 4px;
}

@media (max-width: 860px) {
  /* 手机：隐藏 6 列表格，改用行列表 */
  .desk-table {
    display: none;
  }
  .m-list {
    display: block;
  }
  .m-row {
    padding: 12px 14px;
    border-bottom: 1px solid var(--hairline);
  }
  .m-row:last-child {
    border-bottom: 0;
  }
  .m-empty {
    padding: 32px 14px;
    text-align: center;
    font-size: 0.88rem;
    color: var(--text-3);
  }
  .m-row-top {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .m-cat {
    flex: 0 0 auto;
  }
  .m-note {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.92rem;
    color: var(--text-2);
  }
  .m-amt {
    flex: 0 0 auto;
    font-size: 0.95rem;
    font-weight: 650;
    letter-spacing: -0.01em;
    color: var(--text);
    white-space: nowrap;
  }
  .m-amt.is-income {
    color: var(--live);
  }
  .m-row-sub {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 6px;
  }
  .m-meta {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.78rem;
    color: var(--text-3);
  }
  .m-acts {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    flex: 0 0 auto;
  }
  /* 触控目标 ≥ 44px：视觉图标小、命中区大 */
  .m-act {
    display: inline-grid;
    place-items: center;
    width: 44px;
    height: 44px;
    margin: -6px -4px -6px 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: var(--text-3);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .m-act.is-edit:active {
    color: var(--accent);
  }
  .m-act.is-del:active {
    color: var(--heat);
  }
  /* 手机头部信息换行防挤压 */
  .panel-head {
    flex-wrap: wrap;
    row-gap: 2px;
  }
  /* 分页器触控目标加大 */
  .pager-right :deep(button) {
    min-height: 40px;
  }
  .size-select {
    height: 36px;
  }
}

@media (max-width: 680px) {
  .panel-head {
    padding: 16px 14px 0;
  }
  .pager {
    padding: 12px 14px 14px;
  }
}
</style>
