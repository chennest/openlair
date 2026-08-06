<script setup lang="ts">
// 习惯模块页：新增 + 列表 + 打卡/删除
import { onMounted, ref } from 'vue'
import { habitApi, type Habit } from './api'
import HabitList from './HabitList.vue'

const loading = ref(true)
const error = ref('')
const habits = ref<Habit[]>([])

const newName = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    habits.value = (await habitApi.list()).habits
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createHabit() {
  if (!newName.value.trim()) return
  saving.value = true
  try {
    await habitApi.create(newName.value)
    newName.value = ''
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleDone(h: Habit) {
  const week = [...h.week]
  week[6] = !h.done
  await habitApi.update(h.id, {
    done: !h.done,
    streak: h.done ? Math.max(0, h.streak - 1) : h.streak + 1,
    week,
  })
  await load()
}

async function removeHabit(id: string) {
  await habitApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载习惯…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="habits">
    <form class="composer" @submit.prevent="createHabit">
      <input v-model="newName" placeholder="新习惯名称，如：喝水 8 杯" />
      <button type="submit" :disabled="saving">{{ saving ? '添加中…' : '添加习惯' }}</button>
    </form>

    <HabitList :habits="habits" @toggle="toggleDone" @remove="removeHabit" />
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 18px;
  background: rgba(25, 22, 17, 0.66);
}
.composer input {
  flex: 1;
  min-width: 0;
}
.composer button {
  min-width: 120px;
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
  width: 100%;
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
