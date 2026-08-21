<script setup lang="ts">
// 习惯模块页：新增 + 列表 + 打卡/删除
import { onMounted, ref } from 'vue'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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

async function removeHabit(id: number) {
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
      <Input
        v-model="newName"
        class="composer-input h-11 rounded-[var(--r-thumb)]"
        placeholder="新习惯名称，如：喝水 8 杯"
      />
      <Button type="submit" :disabled="saving" class="composer-submit h-11 rounded-full">
        <Plus class="size-4" />
        {{ saving ? '添加中…' : '添加习惯' }}
      </Button>
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
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.composer-input {
  flex: 1;
  min-width: 0;
}
.composer-submit {
  min-width: 120px;
  padding-inline: 18px;
  font-weight: 600;
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

@media (max-width: 860px) {
  .composer {
    flex-direction: column;
  }
  .composer-submit {
    width: 100%;
  }
}
</style>
