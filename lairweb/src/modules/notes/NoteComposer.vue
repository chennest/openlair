<script setup lang="ts">
// 笔记新增表单（纯展示，emit submit）
import { ref } from 'vue'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
    <Input
      v-model="form.title"
      class="field-title h-11"
      placeholder="笔记标题"
      required
    />
    <Textarea
      v-model="form.summary"
      class="field-summary min-h-20"
      rows="2"
      placeholder="内容摘要…"
    />
    <Input
      v-model="tagsText"
      class="field-tags h-11"
      placeholder="标签，逗号分隔（如：工作, 灵感）"
    />
    <Button type="submit" class="field-submit h-11 rounded-full px-6" :disabled="saving">
      <Plus class="size-4" />
      {{ saving ? '保存中…' : '新增笔记' }}
    </Button>
  </form>
</template>

<style scoped>
.composer {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas:
    'title   submit'
    'summary summary'
    'tags    tags';
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.field-title {
  grid-area: title;
}
.field-submit {
  grid-area: submit;
}
.field-summary {
  grid-area: summary;
}
.field-tags {
  grid-area: tags;
}
@media (max-width: 640px) {
  .composer {
    grid-template-columns: 1fr;
    grid-template-areas:
      'title'
      'summary'
      'tags'
      'submit';
  }
}
</style>
