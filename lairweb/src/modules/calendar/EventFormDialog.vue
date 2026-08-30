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
  saving: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', input: CreateEventInput): void
}>()

/** 当前时刻 HH:mm（作为默认时间） */
function nowTime(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** 今天 YYYY-MM-DD（作为默认日期） */
function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const form = ref<CreateEventInput>({ title: '', date: todayStr(), time: nowTime(), location: '' })

// 打开时重置表单：日期 = 今天（当前），时间 = 当前时刻
watch(
  () => props.open,
  (open) => {
    if (open) form.value = { title: '', date: todayStr(), time: nowTime(), location: '' }
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
      <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">标题</Label>
      <Input v-model="form.title" class="h-11" placeholder="日程标题" autofocus @keyup.enter="submit" />

      <div class="row2">
        <div>
          <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">日期</Label>
          <Input v-model="form.date" class="h-11 w-full" type="date" />
        </div>
        <div>
          <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">时间</Label>
          <Input v-model="form.time" class="h-11 w-full" type="time" />
        </div>
      </div>

      <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">地点（可选）</Label>
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
