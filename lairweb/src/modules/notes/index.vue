<script setup lang="ts">
// 笔记模块页：新增 + 列表 + 删除
import { onMounted, ref } from 'vue'
import { noteApi, type Note } from './api'
import NoteComposer from './NoteComposer.vue'
import NoteCard from './NoteCard.vue'

const loading = ref(true)
const error = ref('')
const notes = ref<Note[]>([])
const composerRef = ref<InstanceType<typeof NoteComposer> | null>(null)

async function load() {
  loading.value = true
  try {
    notes.value = (await noteApi.list()).notes
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createNote(payload: Parameters<typeof noteApi.create>[0]) {
  try {
    await noteApi.create(payload)
    composerRef.value?.reset()
    await load()
  } finally {
    composerRef.value?.reset()
  }
}

async function removeNote(id: string) {
  await noteApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载笔记…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="notes">
    <NoteComposer ref="composerRef" @submit="createNote" />

    <div class="notes-grid">
      <NoteCard
        v-for="n in notes"
        :key="n.id"
        :title="n.title"
        :summary="n.summary"
        :tags="n.tags"
        :updated-at="n.updatedAt"
        @remove="removeNote(n.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.notes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
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
</style>
