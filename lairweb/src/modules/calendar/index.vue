<script setup lang="ts">
// 日历模块页：通用月历网格 + 选中日期日程（新增/完成/删除）
import { computed, onMounted, ref, watch, type Ref } from 'vue'
import type { DateValue } from '@internationalized/date'
import { getLocalTimeZone, today } from '@internationalized/date'
import { toDate } from 'reka-ui/date'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Calendar,
  CalendarCellTrigger,
} from '@/components/ui/calendar'
import { calendarApi, type CalendarEvent } from './api'
import EventList from './EventList.vue'

const loading = ref(true)
const error = ref('')
const events = ref<CalendarEvent[]>([])

const form = ref({ title: '', date: '', time: '10:00', location: '' })
const saving = ref(false)

// ---------- 通用月历状态 ----------
/** 当前选中日期（月历 v-model） */
const selectedDate = ref(today(getLocalTimeZone())) as Ref<DateValue>

/** DateValue → 'YYYY-MM-DD'（与后端契约一致） */
function dayKey(d: DateValue): string {
  return `${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`
}

/** 该日期是否有日程（月历格子小圆点） */
function hasEvents(d: DateValue): boolean {
  const k = dayKey(d)
  return events.value.some((e) => e.date === k)
}

/** 选中日期当天日程 */
const dayEvents = computed(() => {
  const k = dayKey(selectedDate.value)
  return events.value.filter((e) => e.date === k)
})

/** 选中日期标题：8月21日 星期五 */
const dayTitle = computed(() =>
  toDate(selectedDate.value, getLocalTimeZone()).toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }),
)

// 点击日历日期 → 新增表单的日期跟随选中
watch(selectedDate, (d) => {
  form.value.date = dayKey(d)
})

async function load() {
  loading.value = true
  try {
    events.value = (await calendarApi.list()).events
    // 首次加载：表单日期默认今天（若尚未设置）
    if (!form.value.date) form.value.date = dayKey(today(getLocalTimeZone()))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createEvent() {
  if (!form.value.title.trim()) return
  saving.value = true
  try {
    await calendarApi.create(form.value)
    form.value = { title: '', date: dayKey(selectedDate.value), time: '10:00', location: '' }
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleDone(e: CalendarEvent) {
  await calendarApi.update(e.id, { done: !e.done })
  await load()
}

async function removeEvent(id: number) {
  await calendarApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载日程…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="calendar">
    <div class="cal-layout">
      <!-- ═══ 左：通用月历网格 ═══ -->
      <section class="cal-panel">
        <Calendar
          v-model="selectedDate"
          :default-placeholder="today(getLocalTimeZone())"
          weekday-format="short"
          class="rounded-[var(--r-panel)] border bg-card shadow-[var(--sh-panel)]"
        >
          <template #calendar-cell="{ date }">
            <CalendarCellTrigger
              :day="date"
              :month="date"
              class="cal-cell"
            >
              <span class="cal-day-num">{{ date.day }}</span>
              <span v-if="hasEvents(date)" class="cal-dot" aria-hidden="true"></span>
            </CalendarCellTrigger>
          </template>
        </Calendar>
      </section>

      <!-- ═══ 右：选中日期日程 ═══ -->
      <section class="day-panel">
        <div class="day-head">
          <div>
            <h2 class="day-title">{{ dayTitle }}</h2>
            <p class="day-count">{{ dayEvents.length }} 项日程</p>
          </div>
        </div>

        <EventList
          :events="dayEvents"
          :title="'当日日程'"
          @toggle="toggleDone"
          @remove="removeEvent"
        />

        <!-- 新增日程 -->
        <form class="composer" @submit.prevent="createEvent">
          <div class="composer-row">
            <Input
              v-model="form.title"
              class="field-title h-11 flex-1 min-w-[140px]"
              placeholder="日程标题"
              required
            />
            <Input v-model="form.date" class="field-date h-11" type="date" />
            <Input v-model="form.time" class="field-time h-11" type="time" />
          </div>
          <div class="composer-row">
            <Input
              v-model="form.location"
              class="field-location h-11 flex-1 min-w-[140px]"
              placeholder="地点（可选）"
            />
            <Button type="submit" class="field-submit h-11 rounded-full px-5" :disabled="saving">
              <Plus class="size-4" />
              {{ saving ? '添加中…' : '添加' }}
            </Button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════════════
   calendar page — 通用月历网格（reka Calendar）+ 当日日程
   ════════════════════════════════════════════════════════════ */

.cal-layout {
  display: grid;
  grid-template-columns: minmax(320px, 400px) 1fr;
  gap: 18px;
  align-items: start;
}

/* ── 月历面板 ── */
.cal-panel {
  position: sticky;
  top: 20px;
}

/* 格子：44px 触控目标，日程小圆点绝对定位 */
.cal-cell {
  position: relative;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
}

.cal-day-num {
  line-height: 1;
}

.cal-dot {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

/* 今日(未选中):蓝色细描边,与选中蓝底区分 */
.cal-cell[data-today]:not([data-selected]) {
  background: transparent;
  color: var(--accent);
  font-weight: 700;
  box-shadow: inset 0 0 0 1.5px var(--accent);
}

/* 选中态格子的圆点变白（选中蓝底） */
.cal-cell[data-selected] .cal-dot {
  background: #fff;
}

/* ── 右侧：当日日程 ── */
.day-panel {
  min-width: 0;
}

.day-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.day-title {
  margin: 0;
  font-size: clamp(1.3rem, 2.4vw, 1.7rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.15;
}

.day-count {
  margin: 4px 0 0;
  color: var(--text-3);
  font-size: 0.82rem;
}

/* ── 新增表单 ── */
.composer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
  padding: 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

.composer-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.composer-row .field-date,
.composer-row .field-time {
  flex: 0 0 auto;
  width: auto;
}

/* ── 响应式：手机端上下排列 ── */
@media (max-width: 860px) {
  .cal-layout {
    grid-template-columns: 1fr;
  }

  .cal-panel {
    position: static;
  }

  .composer-row {
    flex-direction: column;
  }

  .composer-row .field-date,
  .composer-row .field-time {
    width: 100%;
  }
}
</style>
