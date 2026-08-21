<script setup lang="ts">
// 日历模块页：企业微信式月历 — 格子内嵌日程条（时间+标题）+ 点击弹窗交互
import { onMounted, ref, type Ref } from 'vue'
import type { DateValue } from '@internationalized/date'
import { getLocalTimeZone, today } from '@internationalized/date'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import {
  Calendar,
  CalendarCellTrigger,
} from '@/components/ui/calendar'
import { calendarApi, type CalendarEvent, type CreateEventInput } from './api'
import EventFormDialog from './EventFormDialog.vue'
import EventDetailDialog from './EventDetailDialog.vue'

const loading = ref(true)
const error = ref('')
const events = ref<CalendarEvent[]>([])

// ---------- 月历状态 ----------
/** 当前选中日期 */
const selectedDate = ref(today(getLocalTimeZone())) as Ref<DateValue>
/** 当前显示月份（编程导航用） */
const placeholder = ref(today(getLocalTimeZone())) as Ref<DateValue>

// ---------- 弹窗状态 ----------
const formOpen = ref(false)
const detailOpen = ref(false)
const detailEvent = ref<CalendarEvent | null>(null)
const saving = ref(false)
const busy = ref(false)

/** DateValue → 'YYYY-MM-DD'（与后端契约一致）。入参可能为 null/undefined（reka 网格填充位），返回空串 */
function dayKey(d: DateValue | null | undefined): string {
  if (!d) return ''
  return `${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`
}

/** 某日期当天全部日程（格子渲染用） */
function eventsOf(d: DateValue | null | undefined): CalendarEvent[] {
  const k = dayKey(d)
  if (!k) return []
  return events.value.filter((e) => e.date === k)
}

/** 回到今天 */
function goToday() {
  const t = today(getLocalTimeZone())
  placeholder.value = t
  selectedDate.value = t
}

/** 点击日程条：打开详情弹窗 */
function openDetail(ev: CalendarEvent) {
  detailEvent.value = ev
  detailOpen.value = true
}

async function load() {
  loading.value = true
  try {
    events.value = (await calendarApi.list()).events
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createEvent(input: CreateEventInput) {
  saving.value = true
  try {
    await calendarApi.create(input)
    formOpen.value = false
    // 新日程落在所选月份内时,确保月历停在对应月份
    const [y, m] = input.date.split('-').map(Number)
    if (y && m) placeholder.value = selectedDate.value.set({ year: y, month: m })
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleDone(ev: CalendarEvent) {
  busy.value = true
  try {
    await calendarApi.update(ev.id, { done: !ev.done })
    detailOpen.value = false
    await load()
  } finally {
    busy.value = false
  }
}

async function removeEvent(id: number) {
  busy.value = true
  try {
    await calendarApi.remove(id)
    detailOpen.value = false
    await load()
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载日程…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="calendar">
    <!-- 工具栏：今天 + 新建日程（点击才弹出） -->
    <div class="cal-toolbar">
      <Button variant="outline" size="sm" class="today-btn rounded-full px-4" @click="goToday">
        今天
      </Button>
      <span class="flex-1"></span>
      <Button size="sm" class="new-btn rounded-full px-4" @click="formOpen = true">
        <Plus class="size-4" />
        新建日程
      </Button>
    </div>

    <!-- 月历网格：格子内嵌日程条（企微式） -->
    <Calendar
      v-model="selectedDate"
      v-model:placeholder="placeholder"
      :default-placeholder="today(getLocalTimeZone())"
      locale="zh-CN"
      weekday-format="short"
      class="cal-root"
    >
      <template #calendar-cell="{ date, month }">
        <div v-if="date" class="cal-cell-box">
          <CalendarCellTrigger
            :day="date"
            :month="month"
            class="cal-day-trigger"
          >
            {{ date.day }}
          </CalendarCellTrigger>
          <div class="cal-events">
            <div
              v-for="ev in eventsOf(date).slice(0, 3)"
              :key="ev.id"
              class="cal-ev"
              :class="{ done: ev.done }"
              :title="`${ev.time} ${ev.title}`"
              @click.stop="openDetail(ev)"
            >
              <span class="ev-dot" aria-hidden="true"></span>
              <span class="ev-time">{{ ev.time }}</span>
              <span class="ev-title">{{ ev.title }}</span>
            </div>
            <div
              v-if="eventsOf(date).length > 3"
              class="ev-more"
              @click.stop="selectedDate = date"
            >
              +{{ eventsOf(date).length - 3 }} 个日程
            </div>
          </div>
        </div>
      </template>
    </Calendar>

    <!-- 新建日程弹窗（点击按钮才弹出；日期/时间默认当前） -->
    <EventFormDialog
      :open="formOpen"
      :saving="saving"
      @close="formOpen = false"
      @submit="createEvent"
    />

    <!-- 日程详情弹窗（点击日程条弹出） -->
    <EventDetailDialog
      :open="detailOpen"
      :event="detailEvent"
      :busy="busy"
      @close="detailOpen = false"
      @toggle="toggleDone"
      @remove="removeEvent"
    />
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════════════
   calendar page — 企业微信式月历（格子内嵌日程条）
   ════════════════════════════════════════════════════════════ */

/* ── 工具栏 ── */
.cal-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

/* ── 月历根：白卡面板 ── */
.cal-root {
  width: 100%;
  border: 1px solid var(--hairline);
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

/* ── 格子：定高、内容顶对齐（覆盖 shadcn 默认小格子） ── */
.calendar :deep([data-slot='calendar-cell']) {
  height: 104px;
  align-items: flex-start;
  padding: 6px 4px 4px;
  overflow: hidden;
}

/* 选中日期：整格浅蓝底（非实色） */
.calendar :deep([data-slot='calendar-cell']:has([data-selected])) {
  background: rgba(0, 113, 227, 0.06);
  border-radius: var(--r-thumb);
}

/* ── 格子内：日期数字 + 日程区 ── */
.cal-cell-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  height: 100%;
  gap: 3px;
}

.cal-day-trigger {
  width: 30px;
  height: 30px;
  font-size: 0.84rem;
  font-weight: 500;
  flex: 0 0 auto;
}

/* 今日（未选中）：蓝色细描边，与选中蓝底区分 */
.cal-day-trigger[data-today]:not([data-selected]) {
  background: transparent;
  color: var(--accent);
  font-weight: 700;
  box-shadow: inset 0 0 0 1.5px var(--accent);
}

.cal-events {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  min-height: 0;
}

/* ── 日程条：浅蓝底圆角小块，时间+标题 ── */
.cal-ev {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 1px 6px;
  border-radius: 5px;
  background: rgba(0, 113, 227, 0.09);
  cursor: pointer;
  line-height: 1.5;
  transition: background 140ms ease;
}

.cal-ev:hover {
  background: rgba(0, 113, 227, 0.18);
}

.cal-ev.done {
  background: rgba(0, 0, 0, 0.05);
}

.ev-dot {
  flex: 0 0 auto;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent);
}

.cal-ev.done .ev-dot {
  background: var(--text-4);
}

.ev-time {
  flex: 0 0 auto;
  color: var(--text-2);
  font-size: 0.66rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.cal-ev.done .ev-time {
  color: var(--text-4);
}

.ev-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-size: 0.72rem;
  font-weight: 500;
}

.cal-ev.done .ev-title {
  color: var(--text-3);
  text-decoration: line-through;
}

/* ── “+N 个日程” ── */
.ev-more {
  padding: 0 6px;
  color: var(--accent);
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
}

/* ── 响应式：手机端格子变矮 ── */
@media (max-width: 860px) {
  .calendar :deep([data-slot='calendar-cell']) {
    height: 64px;
    padding: 3px 2px;
  }

  .cal-day-trigger {
    width: 26px;
    height: 26px;
    font-size: 0.78rem;
  }

  .cal-ev {
    padding: 0 4px;
  }

  .cal-events {
    overflow: hidden;
  }
}
</style>
