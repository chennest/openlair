<script setup lang="ts">
// 待办模块页：四象限视图 + 新增/勾选/删除
import { onMounted, ref } from 'vue'
import { Loader2, CircleAlert, Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent } from '@/components/ui/card'
import { todoApi, QUADRANTS, DUES, type TodoItem } from './api'
import QuadrantCard from './QuadrantCard.vue'

const loading = ref(true)
const error = ref('')
const todos = ref<TodoItem[]>([])

const form = ref({ text: '', quadrant: '重要不紧急', due: '今天' })
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    todos.value = (await todoApi.list()).todos
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createTodo() {
  if (!form.value.text.trim()) return
  saving.value = true
  try {
    await todoApi.create(form.value)
    form.value.text = ''
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleDone(item: TodoItem) {
  await todoApi.update(item.id, { done: !item.done })
  await load()
}

async function removeTodo(id: number) {
  await todoApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="empty-state">
    <Card class="empty-card w-full max-w-sm border border-dashed ring-0 shadow-none">
      <CardContent class="flex flex-col items-center gap-3 py-10">
        <Loader2 class="size-6 animate-spin text-[var(--accent)]" />
        <p class="empty-title">正在加载待办…</p>
      </CardContent>
    </Card>
  </div>

  <div v-else-if="error" class="empty-state">
    <Card class="empty-card w-full max-w-sm border border-dashed ring-0 shadow-none">
      <CardContent class="flex flex-col items-center gap-3 py-10">
        <CircleAlert class="size-6 text-[var(--heat)]" />
        <p class="empty-title">{{ error }}</p>
      </CardContent>
    </Card>
  </div>

  <div v-else class="todo">
    <form class="composer" @submit.prevent="createTodo">
      <Input
        v-model="form.text"
        placeholder="新增待办…"
        class="composer-input h-11 min-w-[120px] flex-1"
      />
      <Select v-model="form.quadrant">
        <SelectTrigger class="min-h-11 min-w-[132px]" aria-label="选择象限">
          <SelectValue placeholder="象限" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="q in QUADRANTS" :key="q" :value="q">{{ q }}</SelectItem>
        </SelectContent>
      </Select>
      <Select v-model="form.due">
        <SelectTrigger class="min-h-11 min-w-[104px]" aria-label="选择期限">
          <SelectValue placeholder="期限" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="d in DUES" :key="d" :value="d">{{ d }}</SelectItem>
        </SelectContent>
      </Select>
      <Button type="submit" :disabled="saving" class="h-11 gap-1.5 px-5">
        <Plus class="size-4" />
        {{ saving ? '添加中…' : '添加' }}
      </Button>
    </form>

    <div class="todo-grid">
      <QuadrantCard
        v-for="q in QUADRANTS"
        :key="q"
        :title="q"
        :items="todos.filter((t) => t.quadrant === q)"
        @toggle="toggleDone"
        @remove="removeTodo"
      />
    </div>
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  padding: 12px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.todo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

/* 空状态 / 占位（Card + 图标） */
.empty-state {
  display: grid;
  place-items: center;
  min-height: 46vh;
}
.empty-card {
  border-color: var(--faint);
  border-radius: var(--r-panel);
  background: var(--surface);
}
.empty-title {
  color: var(--text-3);
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .composer {
    flex-wrap: wrap;
  }
  .composer :deep(.composer-input) {
    flex-basis: 100%;
  }
}
</style>
