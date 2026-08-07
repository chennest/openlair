<script setup lang="ts">
// 笔记新增表单（纯展示，emit submit）
import { ref } from 'vue'
import type { CreateNoteInput } from './api'

const emit = defineEmits<{
  (e: 'submit', payload: CreateNoteInput): void
}>()

const saving = ref(false)
const form = ref<CreateNoteInput>({ title: '', summary: '', tags: [] })
const tagsText = ref('')

function submit() {
  if (!form.value.title.trim()) return
  saving.value = true
  emit('submit', {
    title: form.value.title,
    summary: form.value.summary,
    tags: tagsText.value.split(/[,，\s]+/).filter(Boolean),
  })
}

function reset() {
  form.value = { title: '', summary: '', tags: [] }
  tagsText.value = ''
  saving.value = false
}

defineExpose({ reset })
</script>

<template>
  <form class="composer" @submit.prevent="submit">
    <input v-model="form.title" placeholder="笔记标题" required />
    <textarea v-model="form.summary" rows="2" placeholder="内容摘要…"></textarea>
    <input v-model="tagsText" placeholder="标签，逗号分隔（如：工作, 灵感）" />
    <button type="submit" :disabled="saving">{{ saving ? '保存中…' : '新增笔记' }}</button>
  </form>
</template>

<style scoped>
.composer {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.composer textarea {
  grid-column: span 3;
  min-height: 40px;
}
.composer button {
  grid-column: span 3;
}
input,
textarea {
  width: 100%;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  color: var(--text);
  outline: none;
  background: var(--surface);
  padding: 10px 12px;
  font: inherit;
  transition: border-color 160ms ease;
}
input:focus,
textarea:focus {
  border-color: var(--accent);
}
button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
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
button:hover {
  box-shadow: var(--sh-cta);
}
button:active {
  transform: scale(0.97);
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 640px) {
  .composer {
    grid-template-columns: 1fr;
  }
  .composer textarea,
  .composer button {
    grid-column: span 1;
  }
}
</style>
