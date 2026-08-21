<script setup lang="ts">
// 新建日程表单弹窗（基于 BaseModal）
import { ref, watch } from 'vue'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import BaseModal from '../../components/BaseModal.vue'
import type { CreateEventInput } from './api'

const props = defineProps<{
  open: boolean
  /** 默认日期（选中日期） */
  defaultDate: string
  saving: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', input: CreateEventInput): void
}>()

const form = ref<CreateEventInput>({ title: '', date: '', time: '10:00', location: '' })

// 打开时重置表单，日期默认选中日
watch(
  () => props.open,
  (open) => {
    if (open) form.value = { title: '', date: props.defaultDate, time: '10:00', location: '' }
  },
)

function submit() {
  if (!form.value.title.trim() || !form.value.date) return
  emit('submit', { ...form.value })
}
</script>

<template>
  <BaseModal v-if="open" title="新建日程" @close="emit('close')">
    <div class="ev-form">
      <Label class="f-label">标题</Label>
      <Input v-model="form.title" class="h-11" placeholder="日程标题" autofocus @keyup.enter="submit" />

      <div class="row2">
        <div>
          <Label class="f-label">日期</Label>
          <Input v-model="form.date" class="h-11 w-full" type="date" />
        </div>
        <div>
          <Label class="f-label">时间</Label>
          <Input v-model="form.time" class="h-11 w-full" type="time" />
        </div>
      </div>

      <Label class="f-label">地点（可选）</Label>
      <Input v-model="form.location" class="h-11" placeholder="地点" @keyup.enter="submit" />

      <div class="foot">
        <Button variant="outline" @click="emit('close')">取消</Button>
        <Button :disabled="saving || !form.title.trim() || !form.date" @click="submit">
          <Plus class="size-4" />
          {{ saving ? '保存中…' : '创建日程' }}
        </Button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.ev-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}

.f-label {
  margin-top: 10px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 600;
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}
</style>
