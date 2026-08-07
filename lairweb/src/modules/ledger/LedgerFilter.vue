<script setup lang="ts">
// 历史查询筛选栏：类型 segmented / 日期快捷范围 / 分类 / 关键字
// 纯展示：props 进（当前值 + 分类列表），交互 emit change（完整 query 变更）
import { ref } from 'vue'
import type { Category, LedgerQuery } from './api'

defineProps<{
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

// 当前档位（自定义日期时显示为「自定义」）
const preset = ref<DatePreset>('')

function change(patch: Partial<LedgerQuery>) {
  emit('change', { ...patch })
}

function pickPreset(key: DatePreset) {
  preset.value = key
  change({ ...rangeOf(key), page: 1 })
}

function pickType(type: LedgerQuery['type']) {
  // 切换类型时若当前分类属于另一类型则清空
  change({ type, categoryId: undefined, page: 1 })
}

function pickCategory(categoryId: string) {
  change({ categoryId: categoryId || undefined, page: 1 })
}

function clearAll() {
  preset.value = ''
  emit('change', { page: 1 })
}
</script>

<template>
  <div class="filter">
    <!-- 类型 segmented（白胶囊，components.md §5） -->
    <div class="seg" role="tablist" aria-label="交易类型">
      <button
        class="seg-btn"
        :class="{ on: !value.type }"
        @click="pickType('')"
      >全部</button>
      <button
        class="seg-btn"
        :class="{ on: value.type === '支出' }"
        @click="pickType('支出')"
      >支出</button>
      <button
        class="seg-btn"
        :class="{ on: value.type === '收入' }"
        @click="pickType('收入')"
      >收入</button>
    </div>

    <!-- 日期快捷 -->
    <div class="presets" role="tablist" aria-label="日期范围">
      <button
        v-for="p in PRESETS"
        :key="p.key"
        class="preset-btn"
        :class="{ on: preset === p.key }"
        @click="pickPreset(p.key)"
      >{{ p.label }}</button>
    </div>

    <!-- 分类 -->
    <select class="select" :value="value.categoryId ?? ''" @change="pickCategory(($event.target as HTMLSelectElement).value)">
      <option value="">全部分类</option>
      <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
    </select>

    <!-- 关键字 -->
    <input
      class="kw"
      :value="value.keyword ?? ''"
      placeholder="搜索备注 / 分类"
      @input="change({ keyword: ($event.target as HTMLInputElement).value, page: 1 })"
    />

    <button v-if="value.type || value.categoryId || value.keyword || value.startDate" class="reset" @click="clearAll">
      重置
    </button>
  </div>
</template>

<style scoped>
.filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  padding: 12px 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.seg {
  display: inline-flex;
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--r-pill);
  padding: 3px;
  gap: 2px;
}
.seg-btn {
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: var(--r-pill);
  background: transparent;
  color: var(--text-2);
  transition: all 200ms var(--ease-out-quart);
}
.seg-btn.on {
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}
.presets {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
}
.preset-btn {
  border: none;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 500;
  padding: 6px 11px;
  border-radius: var(--r-pill);
  background: transparent;
  color: var(--text-2);
  transition: all 160ms ease;
}
.preset-btn:hover {
  color: var(--text);
  background: rgba(0, 0, 0, 0.04);
}
.preset-btn.on {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.08);
  font-weight: 600;
}
.select,
.kw {
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  color: var(--text);
  outline: none;
  background: var(--surface);
  padding: 7px 14px;
  font-size: 13px;
  font: inherit;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.kw {
  min-width: 180px;
}
.select:focus,
.kw:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
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
