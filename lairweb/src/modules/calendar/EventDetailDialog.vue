<script setup lang="ts">
// 日程详情弹窗：信息展示 + 标记完成/删除（基于 BaseModal）
import { Check, Trash2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import BaseModal from '../../components/BaseModal.vue'
import type { CalendarEvent } from './api'

defineProps<{
  open: boolean
  event: CalendarEvent | null
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'toggle', ev: CalendarEvent): void
  (e: 'remove', id: number): void
}>()
</script>

<template>
  <BaseModal
    v-if="open && event"
    :title="event.title"
    @close="emit('close')"
  >
    <div class="ev-detail">
      <div class="meta-list">
        <div class="meta-row">
          <span class="k">时间</span>
          <span class="v">{{ event.date }} {{ event.time }}</span>
        </div>
        <div class="meta-row">
          <span class="k">地点</span>
          <span class="v">{{ event.location || '未填写' }}</span>
        </div>
        <div class="meta-row">
          <span class="k">状态</span>
          <span class="v" :class="{ done: event.done }">
            {{ event.done ? '已完成' : '待完成' }}
          </span>
        </div>
      </div>

      <div class="foot">
        <Button
          variant="outline"
          class="text-[var(--text-3)] hover:border-[rgba(255,59,48,0.35)] hover:text-[var(--destructive)]"
          :disabled="busy"
          @click="emit('remove', event.id)"
        >
          <Trash2 class="size-4" />
          删除
        </Button>
        <Button
          class="toggle-btn"
          :class="event.done ? 'bg-[var(--live)] text-white hover:bg-[var(--live)]/85' : ''"
          :disabled="busy"
          @click="emit('toggle', event)"
        >
          <Check class="size-4" />
          {{ event.done ? '标记未完成' : '标记完成' }}
        </Button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.ev-detail {
  padding: 4px 0;
}

.meta-list {
  border-radius: var(--r-card);
  background: var(--hover);
  overflow: hidden;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
}

.meta-row:last-child {
  border-bottom: 0;
}

.k {
  flex: 0 0 44px;
  color: var(--text-3);
  font-size: 0.82rem;
}

.v {
  color: var(--text);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.v.done {
  color: var(--live);
}

.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
