<script setup lang="ts">
// 待办模块页：四象限视图 + 新增/勾选/删除
import { onMounted, ref } from 'vue'
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

async function removeTodo(id: string) {
  await todoApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载待办…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="todo">
    <form class="composer" @submit.prevent="createTodo">
      <input v-model="form.text" placeholder="新增待办…" required />
      <select v-model="form.quadrant">
        <option v-for="q in QUADRANTS" :key="q" :value="q">{{ q }}</option>
      </select>
      <select v-model="form.due">
        <option v-for="d in DUES" :key="d" :value="d">{{ d }}</option>
      </select>
      <button type="submit" :disabled="saving">{{ saving ? '添加中…' : '添加' }}</button>
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
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 18px;
  background: rgba(25, 22, 17, 0.66);
}
.composer input {
  flex: 1;
  min-width: 120px;
}
.todo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
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
input,
select {
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 12px;
  color: #f2eadf;
  outline: none;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px 12px;
  font: inherit;
}
select option {
  color: #14120f;
}
input:focus,
select:focus {
  border-color: rgba(246, 211, 122, 0.7);
}
.composer button {
  min-width: 90px;
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
@media (max-width: 640px) {
  .composer {
    flex-wrap: wrap;
  }
  .composer input {
    flex-basis: 100%;
  }
}
</style>
