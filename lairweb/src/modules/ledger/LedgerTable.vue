<script setup lang="ts">
// 流水表格：shadcn Table + 完整分页器（每页条数 / 共 N 条 / 页码 / 上下页）
// 纯展示：props 进，交互 emit 出（remove / page / page-size）
import { computed } from 'vue'
import { ChevronLeft, ChevronRight, X } from '@lucide/vue'
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

    <Table>
      <TableHeader>
        <TableRow class="hover:bg-transparent!">
          <TableHead class="w-[70px] pl-1">日期</TableHead>
          <TableHead class="w-[92px]">分类</TableHead>
          <TableHead>备注</TableHead>
          <TableHead v-if="shared" class="w-[110px]">记账人</TableHead>
          <TableHead class="w-[120px] text-right pr-6">金额</TableHead>
          <TableHead class="w-[52px] text-right pr-1"><span class="sr-only">操作</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableEmpty v-if="transactions.length === 0" :colspan="shared ? 6 : 5">
          没有符合条件的记录，试试调整筛选条件。
        </TableEmpty>
        <TableRow v-for="t in transactions" :key="t.id">
          <TableCell class="pl-1 text-[0.82rem] text-[var(--text-3)] tabular-nums">{{ fmtDate(t.date) }}</TableCell>
          <TableCell>
            <Badge variant="secondary" class="text-[0.72rem] font-semibold text-[var(--text-2)]!">{{ t.category }}</Badge>
          </TableCell>
          <TableCell class="max-w-0">
            <span class="block truncate text-[var(--text-2)]" :title="t.note || ''">{{ t.note || '—' }}</span>
          </TableCell>
          <TableCell v-if="shared">
            <span class="inline-flex items-center gap-1.5 text-[0.82rem] text-[var(--text-3)]" :title="`${t.userName} 记的`">
              <span class="face" aria-hidden="true">{{ t.userName.slice(0, 1) }}</span>
              {{ t.userName }}
            </span>
          </TableCell>
          <TableCell
            class="pr-6 text-right font-semibold tabular-nums"
            :class="t.type === '收入' ? 'text-[var(--live)]' : 'text-[var(--text)]'"
          >
            {{ t.type === '收入' ? '+' : '-' }}¥{{ Number(t.amount).toFixed(2) }}
          </TableCell>
          <TableCell class="pr-1 text-right">
            <Button
              variant="ghost"
              size="icon-sm"
              class="text-[var(--text-3)] hover:text-[var(--heat)]! hover:bg-transparent"
              aria-label="删除"
              @click="emit('remove', t.id)"
            >
              <X class="size-3.5" />
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <!-- 分页器 -->
    <nav v-if="total > 0" class="pager" aria-label="分页">
      <div class="pager-left">
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
@media (max-width: 680px) {
  .panel-head {
    padding: 16px 14px 0;
  }
  .pager {
    padding: 12px 14px 14px;
  }
}
</style>
