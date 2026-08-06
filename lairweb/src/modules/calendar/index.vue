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
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 18px;
  background: rgba(25, 22, 17, 0.66);
}
.composer input:first-child {
  flex: 1;
  min-width: 160px;
}
.composer button {
  min-width: 110px;
  padding: 11px 16px;
  border-radius: 12px;
  border: 0;
  color: #14120f;
  background: #f6d37a;
  font-weight: 800;
  cursor: pointer;
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
  border: 1px dashed rgba(242, 234, 223, 0.16);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.4);
  color: rgba(242, 234, 223, 0.48);
}
.placeholder .symbol {
  font-size: 2.4rem;
  margin-bottom: 12px;
  color: rgba(246, 211, 122, 0.7);
}
input {
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 12px;
  color: #f2eadf;
  outline: none;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px 12px;
  font: inherit;
}
input:focus {
  border-color: rgba(246, 211, 122, 0.7);
}
</style>
