<script setup lang="ts">
// 日历模块页：日程列表 + 新增/完成/删除
import { onMounted, ref } from 'vue'
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

async function removeEvent(id: string) {
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
      <input v-model="form.title" placeholder="日程标题" required />
      <input v-model="form.date" type="date" />
      <input v-model="form.time" type="time" />
      <input v-model="form.location" placeholder="地点（可选）" />
      <button type="submit" :disabled="saving">{{ saving ? '添加中…' : '添加日程' }}</button>
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
.composer input:first-child {
  flex: 1;
  min-width: 160px;
}
.composer button {
  display: inline-flex;
  align-items: center;
  min-width: 110px;
  height: 44px;
  padding: 0 16px;
  border-radius: var(--r-pill);
  border: 0;
  color: #fff;
  background: var(--accent);
  font-weight: 600;
  cursor: pointer;
  transition: transform 160ms var(--ease-out-quart), box-shadow 160ms var(--ease-out-quart);
}
.composer button:hover {
  box-shadow: var(--sh-cta);
}
.composer button:active {
  transform: scale(0.97);
}
.composer button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
input {
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  color: var(--text);
  outline: none;
  background: var(--surface);
  padding: 10px 12px;
  font: inherit;
  transition: border-color 160ms ease;
}
input:focus {
  border-color: var(--accent);
}
</style>
