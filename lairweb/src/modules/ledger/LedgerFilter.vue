<script setup lang="ts">
// 历史查询筛选栏：类型 segmented / 日期快捷范围 / 分类 / 关键字
// 纯展示：props 进（当前值 + 分类列表），交互 emit change（完整 query 变更）
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { Category, LedgerQuery } from './api'

const props = defineProps<{
  categories: Category[]
  value: LedgerQuery
}>()

const emit = defineEmits<{
  (e: 'change', query: LedgerQuery): void
}>()

// ---------- 日期快捷档位 ----------
export type DatePreset = '' | 'today' | 'week' | 'month' | 'month3'
const PRESETS: { key: DatePreset; label: string }[] = [
  { key: '', label: '全部' },
  { key: 'today', label: '今天' },
  { key: 'week', label: '近 7 天' },
  { key: 'month', label: '本月' },
  { key: 'month3', label: '近 3 月' },
]

const pad = (n: number) => String(n).padStart(2, '0')
const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function rangeOf(preset: DatePreset): { startDate?: string; endDate?: string } {
  const now = new Date()
  switch (preset) {
    case 'today':
      return { startDate: fmt(now), endDate: fmt(now) }
    case 'week': {
      const s = new Date(now)
      s.setDate(now.getDate() - 6)
      return { startDate: fmt(s), endDate: fmt(now) }
    }
    case 'month':
      return { startDate: fmt(new Date(now.getFullYear(), now.getMonth(), 1)), endDate: fmt(now) }
    case 'month3': {
      const s = new Date(now.getFullYear(), now.getMonth() - 2, 1)
      return { startDate: fmt(s), endDate: fmt(now) }
    }
    default:
      return {}
  }
}

// 当前档位：由 props.value 推导（受控）,保证与父组件 query 状态一致
// （切账本/清空后父组件重置 query,此处自动回到"全部",不会残留错误高亮）
const preset = computed<DatePreset>(() => {
  const v = props.value
  if (v.startDate && v.endDate) {
    const now = new Date()
    const today = fmt(now)
    const s = new Date(now)
    s.setDate(now.getDate() - 6)
    if (v.startDate === today && v.endDate === today) return 'today'
    if (v.startDate === fmt(s) && v.endDate === today) return 'week'
    if (v.startDate === fmt(new Date(now.getFullYear(), now.getMonth(), 1)) && v.endDate === today) return 'month'
    if (v.startDate === fmt(new Date(now.getFullYear(), now.getMonth() - 2, 1)) && v.endDate === today) return 'month3'
  }
  return ''
})

function change(patch: Partial<LedgerQuery>) {
  emit('change', { ...patch })
}

function pickPreset(key: DatePreset) {
  // 解构强制携带键:rangeOf('') 返回 {},若直接展开则 patch 无 startDate/endDate 键,
  // 父组件合并后旧日期残留,"全部"会失效。解构后始终带键(值为 undefined = 清除)。
  const { startDate, endDate } = rangeOf(key)
  change({ startDate, endDate, page: 1 })
}

function pickType(type: LedgerQuery['type']) {
  // 切换类型时若当前分类属于另一类型则清空
  change({ type, categoryId: undefined, page: 1 })
}

function pickCategory(categoryId: number) {
  change({ categoryId: categoryId || undefined, page: 1 })
}

function clearAll() {
  // 完整清除:日期范围/类型/分类/关键字全部重置(否则父组件合并后 startDate 等残留,重置不生效)
  emit('change', {
    page: 1,
    startDate: undefined,
    endDate: undefined,
    type: undefined,
    categoryId: undefined,
    keyword: undefined,
  })
}

// ---------- shadcn 控件适配（Tabs / Select 的值用字符串键映射） ----------
const typeKey = computed({
  get: () => (props.value.type === '支出' ? '支出' : props.value.type === '收入' ? '收入' : 'all'),
  set: (k: string) => pickType(k === 'all' ? '' : (k as '支出' | '收入')),
})

const catKey = computed({
  get: () => (props.value.categoryId ? String(props.value.categoryId) : 'all'),
  set: (v: string) => pickCategory(v === 'all' ? 0 : Number(v)),
})
</script>

<template>
  <div class="filter">
    <!-- 类型 segmented（Tabs 白胶囊） -->
    <Tabs v-model="typeKey">
      <TabsList class="seg">
        <TabsTrigger
          value="all"
          class="h-auto flex-0 px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
        >全部</TabsTrigger>
        <TabsTrigger
          value="支出"
          class="h-auto flex-0 px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
        >支出</TabsTrigger>
        <TabsTrigger
          value="收入"
          class="h-auto flex-0 px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
        >收入</TabsTrigger>
      </TabsList>
    </Tabs>

    <!-- 日期快捷 -->
    <div class="presets" role="tablist" aria-label="日期范围">
      <Button
        v-for="p in PRESETS"
        :key="p.key"
        variant="ghost"
        size="sm"
        class="text-[12.5px] font-medium px-3 rounded-full text-[var(--text-2)]"
        :class="
          preset === p.key
            ? 'bg-[rgba(0,113,227,0.08)] text-[var(--accent)] font-semibold hover:bg-[rgba(0,113,227,0.14)]'
            : ''
        "
        @click="pickPreset(p.key)"
      >{{ p.label }}</Button>
    </div>

    <!-- 分类 -->
    <Select v-model="catKey">
      <SelectTrigger class="cat-select">
        <SelectValue placeholder="全部分类" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">全部分类</SelectItem>
        <SelectItem v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</SelectItem>
      </SelectContent>
    </Select>

    <!-- 关键字 -->
    <Input
      class="kw"
      :model-value="value.keyword ?? ''"
      placeholder="搜索备注 / 分类"
      @update:model-value="change({ keyword: String($event), page: 1 })"
    />

    <Button
      v-if="value.type || value.categoryId || value.keyword || value.startDate"
      variant="ghost"
      size="sm"
      class="reset"
      @click="clearAll"
    >
      <RotateCcw class="size-3.5" />
      重置
    </Button>
  </div>
</template>

<style scoped>
.filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 0 0 14px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--hairline);
}
.seg {
  height: auto;
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--r-pill);
  padding: 3px;
  gap: 2px;
}
.presets {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
}
.cat-select {
  height: 36px;
  border-radius: var(--r-pill);
  padding: 0 14px;
  font-size: 13px;
  background: var(--surface);
  border-color: var(--hairline);
  min-width: 120px;
}
.kw {
  min-width: 180px;
  height: 36px;
  border-radius: var(--r-pill);
  padding: 0 14px;
  font-size: 13px;
}
.reset {
  margin-left: auto;
  border: none;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-2);
  background: transparent;
  padding: 6px 10px;
  border-radius: var(--r-pill);
}
.reset:hover {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
}
@media (max-width: 640px) {
  .filter {
    gap: 8px;
  }
  .kw {
    min-width: 0;
    flex: 1;
  }
}
</style>
