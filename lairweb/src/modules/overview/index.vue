<script setup lang="ts">
// 总览模块页：本月支出 / 待办 / 日程 / 习惯 四卡聚合
import { computed, onMounted, ref } from 'vue'
import {
  Loader2,
  ArrowUpRight,
  Wallet,
  ListTodo,
  CalendarDays,
  Flame,
  TrendingUp,
  TrendingDown,
  CircleAlert,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
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

/** 标签配色：tagClass → shadcn Badge 自定义 Tailwind utility（覆盖 secondary 默认灰）
    ⚠ Badge 根是 reka Primitive，父组件 scoped 类不穿透，配色必须走 utility */
const TAG_TONES: Record<string, string> = {
  red: 'text-[var(--heat)] bg-[var(--heat-bg)]',
  green: 'text-[#0a5a2c] bg-[rgba(48,209,88,0.16)]',
  gold: 'text-white bg-[var(--accent)]',
  gray: 'text-[var(--text-2)] bg-[rgba(0,0,0,0.05)]',
}
function badgeTone(tagClass: string): string {
  return TAG_TONES[tagClass] ?? 'badge-gray'
}
</script>

<template>
  <div v-if="loading" class="empty-state">
    <Card class="w-full max-w-sm border border-dashed border-[var(--faint)] ring-0 shadow-none">
      <CardContent class="flex flex-col items-center gap-3 py-10">
        <Loader2 class="size-6 animate-spin text-[var(--accent)]" />
        <p class="empty-title">正在加载总览…</p>
      </CardContent>
    </Card>
  </div>

  <div v-else-if="error" class="empty-state">
    <Card class="w-full max-w-sm border border-dashed border-[var(--faint)] ring-0 shadow-none">
      <CardContent class="flex flex-col items-center gap-3 py-10">
        <CircleAlert class="size-6 text-[var(--heat)]" />
        <p class="empty-title">{{ error }}</p>
        <small class="empty-sub">请确认 mock server 已启用</small>
      </CardContent>
    </Card>
  </div>

  <section v-else class="card-grid" aria-label="今日概览">
    <article class="card">
      <div class="card-title">
        <span class="title-label"><Wallet class="size-4" />本月支出</span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="h-7 gap-1 px-2 text-xs font-medium text-[var(--text-3)] hover:bg-transparent hover:text-[var(--accent)]"
        >
          查看明细 <ArrowUpRight class="size-3.5" />
        </Button>
      </div>
      <div class="big-num">¥{{ Number(data?.monthExpense.amount).toFixed(2) }}<small>预算 ¥{{ Number(data?.monthExpense.budget).toFixed(0) }}</small></div>
      <Progress :model-value="budgetPercent" class="mt-3.5 h-1.5" aria-label="预算使用率" />
      <p class="hint">
        <TrendingUp v-if="Number(data?.monthExpense.trend) > 0" class="size-3.5 hint-up" />
        <TrendingDown v-else class="size-3.5 hint-down" />
        <span>较上月同期 {{ Math.abs(Number(data?.monthExpense.trend)) }}%</span>
      </p>
    </article>

    <article class="card">
      <div class="card-title">
        <span class="title-label"><ListTodo class="size-4" />待办事项</span>
        <Button type="button" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs font-medium text-[var(--text-3)] hover:bg-transparent hover:text-[var(--accent)]">
          全部待办 <ArrowUpRight class="size-3.5" />
        </Button>
      </div>
      <div class="row-list">
        <div v-for="item in data?.todos" :key="item.text" class="row">
          <span class="main text">{{ item.text }}</span>
          <Badge variant="secondary" :class="badgeTone(item.tagClass)">{{ item.tag }}</Badge>
        </div>
      </div>
    </article>

    <article class="card">
      <div class="card-title">
        <span class="title-label"><CalendarDays class="size-4" />今日日程</span>
        <Button type="button" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs font-medium text-[var(--text-3)] hover:bg-transparent hover:text-[var(--accent)]">
          查看日历 <ArrowUpRight class="size-3.5" />
        </Button>
      </div>
      <div class="row-list">
        <div v-for="item in data?.upcoming" :key="item.text" class="row">
          <span class="main text">{{ item.text }}</span>
          <span class="sub">{{ item.date }}</span>
        </div>
      </div>
    </article>

    <article class="card">
      <div class="card-title">
        <span class="title-label"><Flame class="size-4" />习惯打卡</span>
        <Button type="button" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs font-medium text-[var(--text-3)] hover:bg-transparent hover:text-[var(--accent)]">
          全部习惯 <ArrowUpRight class="size-3.5" />
        </Button>
      </div>
      <div class="row-list">
        <div v-for="item in data?.habits" :key="item.name" class="row">
          <span class="main text">{{ item.name }}</span>
          <Badge variant="secondary" :class="badgeTone(item.done ? 'green' : 'gray')">
            {{ item.done ? '已完成' : '待打卡' }}
          </Badge>
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
.title-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.title-label svg {
  color: var(--text-3);
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
.hint {
  margin: 6px 0 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-2);
  font-size: 0.82rem;
  line-height: 1.6;
}
.hint-up {
  color: var(--heat);
}
.hint-down {
  color: var(--live);
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

/* 空状态 / 占位（Card + 图标） */
.empty-state {
  display: grid;
  place-items: center;
  min-height: 46vh;
}
.empty-title {
  color: var(--text-3);
  font-size: 0.9rem;
}
.empty-sub {
  color: var(--text-4);
  font-size: 0.82rem;
}
</style>
