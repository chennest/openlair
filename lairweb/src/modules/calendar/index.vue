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
import { dayInfo } from '@/lib/holidays'
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

// ---------- 节假日 / 调休 标注 ----------

/**
 * 格子标注内容。只标两类「需要你知道」的信息：
 * - 法定节假日 → 节日短名（红）
 * - 调休补班   → 班（蓝）
 *
 * 普通工作日与普通周末一律不标：周末靠列位置就能识别，全标「休」只是噪音，
 * 反而会把真正需要提醒的「班」淹掉。
 */
interface CellBadge {
  text: string
  kind: 'holiday' | 'makeup'
  title: string
}

/** 标注缓存：节假日数据为静态常量，跨月导航可直接复用（键 = 'YYYY-MM-DD'） */
const badgeCache = new Map<string, CellBadge | null>()

/** 节日短名：超过 2 字时去掉末尾「节」（清明/劳动/端午/中秋/国庆），2 字原样保留（元旦/春节） */
function shortFestival(name: string): string {
  return name.length > 2 ? name.slice(0, -1) : name
}

/** 格子标注；返回 null 表示不标（普通工作日 / 普通周末） */
function cellBadge(d: DateValue | null | undefined): CellBadge | null {
  const k = dayKey(d)
  if (!k || !d) return null
  const cached = badgeCache.get(k)
  if (cached !== undefined) return cached

  // 注意：按该日期自身的年月日构造，跨年月份（如 12 月视图含次年 1 月）也能取对配置
  const info = dayInfo(new Date(d.year, d.month - 1, d.day))
  let badge: CellBadge | null = null
  if (info.kind === 'holiday') {
    const name = info.name ?? '节日'
    badge = { text: shortFestival(name), kind: 'holiday', title: `法定节假日：${name}` }
  } else if (info.kind === 'work' && info.isMakeupWorkday) {
    badge = { text: '班', kind: 'makeup', title: `调休补班（补 ${info.name}）` }
  }
  badgeCache.set(k, badge)
  return badge
}

/** 相邻月份的格子（reka 月网格含上月尾 / 下月头）→ 徽标淡化，不抢当前月视线 */
function isOutsideMonth(d: DateValue | null | undefined, month: DateValue): boolean {
  if (!d) return false
  return d.month !== month.month || d.year !== month.year
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
          <div class="cal-day-head">
            <CalendarCellTrigger
              :day="date"
              :month="month"
              class="cal-day-trigger"
            >
              {{ date.day }}
            </CalendarCellTrigger>
            <span
              v-if="cellBadge(date)"
              class="cal-day-badge"
              :class="[cellBadge(date)!.kind, { outside: isOutsideMonth(date, month) }]"
              :title="cellBadge(date)!.title"
            >{{ cellBadge(date)!.text }}</span>
          </div>
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

/* ── 月历根：白卡面板（Calendar 根是 reka Primitive，scoped 类不穿透 → :deep 从页面根命中） ── */
.calendar :deep(.cal-root) {
  width: 100%;
  border: 1px solid var(--hairline);
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

/* ── 格子：定高 + 淡网格线（覆盖 shadcn 默认小格子） ── */
.calendar :deep([data-slot='calendar-cell']) {
  height: 84px;
  align-items: flex-start;
  padding: 5px 4px 4px;
  overflow: hidden;
  border-top: 1px solid var(--hairline);
  /* flex 项默认 min-width:auto 会被事件条撑破容器（窄屏下整个网格溢出、末两列被切） */
  min-width: 0;
}

/* 纵向分隔线：每行首个格子不加，避免出现最左侧外框线 */
.calendar :deep([data-slot='calendar-cell'] + [data-slot='calendar-cell']) {
  border-left: 1px solid var(--hairline);
}

/* 行间距归零：shadcn 的行自带 mt-2，会把纵向网格线断成一截一截 */
.calendar :deep([data-slot='calendar-grid-row']) {
  margin-top: 0;
}

/* 选中日期：去掉整格浅蓝底（那一大块空蓝框是最显眼的"空"），
   选中态只由数字上的蓝色圆点表达 */
.calendar :deep([data-slot='calendar-cell']:has([data-selected])) {
  background: transparent;
}

/* ── 格子内：日期 + 标注居中，日程区左对齐 ── */
.cal-cell-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  height: 100%;
  gap: 2px;
}

/* CalendarCellTrigger 根是 reka Primitive，scoped 类不穿透 → :deep 从页面根命中 */
.calendar :deep(.cal-day-trigger) {
  width: 30px;
  height: 30px;
  font-size: 0.84rem;
  font-weight: 500;
  flex: 0 0 auto;
  border-radius: 50%;
}

/* 今日（未选中）：蓝色细描边圆 + 蓝字，与选中实心圆区分 */
.calendar :deep(.cal-day-trigger[data-today]:not([data-selected])) {
  background: transparent;
  color: var(--accent);
  font-weight: 700;
  box-shadow: inset 0 0 0 1.5px var(--accent);
}

/* ── 日期头：数字在上、节日名/「班」居中在下 ── */
.cal-day-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  width: 100%;
  flex: 0 0 auto;
}

/* 两类标注：只上色、不做药丸底。
   节日（正红，喜庆而非告警）/ 调休补班（蓝，与顶栏「上班」同色） */
.cal-day-badge {
  flex: 0 0 auto;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.cal-day-badge.holiday {
  color: #d70015;
}

.cal-day-badge.makeup {
  color: var(--accent);
}

/* 相邻月份的格子（上月尾 / 下月头）：标注淡化，不抢当前月视线 */
.cal-day-badge.outside {
  opacity: 0.4;
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
  min-width: 0;
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
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--text-2);
  font-size: 0.66rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.cal-ev.done .ev-time {
  color: var(--text-4);
}

.ev-title {
  flex: 1 1 0;
  /* 关键：nowrap 文本会撑出固有最小宽度，导致窄屏下整个网格溢出（末两列被切）。
     width:0 + flex-grow:1 让它只吃剩余空间，配合 overflow/ellipsis 正常截断。 */
  width: 0;
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
    height: 72px;
    padding: 3px 2px;
  }

  .calendar :deep(.cal-day-trigger) {
    width: 24px;
    height: 24px;
    font-size: 0.72rem;
  }

  /* 标注现在独占一行、居中，不再和数字抢横向空间，故保留两字完整文案；
     字号守住 11px 下限 —— 8px 的中文字形会糊成一团 */
  .cal-day-badge {
    font-size: 0.7rem;
    line-height: 1.2;
  }

  /* 窄屏格子放不下「时间 + 标题」两段，只留圆点 + 标题（时间点开日程详情可见） */
  .ev-time {
    display: none;
  }

  .cal-ev {
    padding: 0 4px;
  }

  .cal-events {
    overflow: hidden;
  }
}
</style>
