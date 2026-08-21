<script setup lang="ts">
// 日历模块页：日程列表 + 新增/完成/删除
import { onMounted, ref } from 'vue'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { calendarApi, type CalendarEvent } from './api'
import EventList from './EventList.vue'

const loading = ref(true)
const error = ref('')
const events = ref<CalendarEvent[]>([])

const form = ref({ title: '', date: '', time: '10:00', location: '' })
const saving = ref(false)

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

async function createEvent() {
  if (!form.value.title.trim()) return
  saving.value = true
  try {
    await calendarApi.create(form.value)
    form.value = { title: '', date: '', time: '10:00', location: '' }
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
    <form class="composer" @submit.prevent="createEvent">
      <Input v-model="form.title" class="field-title h-11" placeholder="日程标题" required />
      <Input v-model="form.date" class="field-date h-11" type="date" />
      <Input v-model="form.time" class="field-time h-11" type="time" />
      <Input v-model="form.location" class="field-location h-11" placeholder="地点（可选）" />
      <Button type="submit" class="field-submit h-11 rounded-full px-5" :disabled="saving">
        <Plus class="size-4" />
        {{ saving ? '添加中…' : '添加日程' }}
      </Button>
    </form>

    <EventList :events="events" @toggle="toggleDone" @remove="removeEvent" />
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.field-title {
  flex: 1 1 160px;
}
.field-date {
  flex: 0 0 auto;
  min-width: 140px;
}
.field-time {
  flex: 0 0 auto;
  min-width: 110px;
}
.field-location {
  flex: 1 1 140px;
}
.field-submit {
  flex: 0 0 auto;
}
.placeholder {
  display: grid;
  place-items: center;
  min-height: 46vh;
  text-align: center;
  border: 1px dashed var(--faint);
  border-radius: var(--r-panel);
  background: var(--surface);
  color: var(--text-3);
}
.placeholder .symbol {
  font-size: 2.4rem;
  margin-bottom: 12px;
  color: var(--accent);
}
@media (max-width: 640px) {
  .field-title,
  .field-location {
    flex-basis: 100%;
  }
  .field-date,
  .field-time {
    flex: 1 1 auto;
  }
}
</style>
