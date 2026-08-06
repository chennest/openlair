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
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 18px;
  background: rgba(25, 22, 17, 0.66);
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
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 12px;
  color: #f2eadf;
  outline: none;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px 12px;
  font: inherit;
}
input:focus,
textarea:focus {
  border-color: rgba(246, 211, 122, 0.7);
}
button {
  min-width: 120px;
  padding: 11px 16px;
  border-radius: 12px;
  border: 0;
  color: #14120f;
  background: #f6d37a;
  font-weight: 800;
  cursor: pointer;
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
