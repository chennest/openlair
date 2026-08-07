<script setup lang="ts">
// 日程列表（纯展示 + 完成/删除）
import Tag from '../../components/Tag.vue'
import type { CalendarEvent } from './api'

defineProps<{ events: CalendarEvent[] }>()

const emit = defineEmits<{
  (e: 'toggle', item: CalendarEvent): void
  (e: 'remove', id: string): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>近期日程</span>
      <Tag variant="green">{{ events.length }} 项</Tag>
    </div>
    <div class="row-list">
      <div v-for="e in events" :key="e.id" class="row">
        <span class="main" @click="emit('toggle', e)">
          <span class="dot-line" :class="{ done: e.done }" aria-hidden="true"></span>
          <span class="text" :class="{ done: e.done }">{{ e.title }}</span>
        </span>
        <span class="sub">
          <span>{{ e.date }} · {{ e.time }} · {{ e.location || '未填地点' }}</span>
          <button class="mini ghost" @click.stop="emit('remove', e.id)">✕</button>
        </span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  padding: 22px 22px 20px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.row-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
}
.row:last-child {
  border-bottom: 0;
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  cursor: pointer;
}
.dot-line {
  width: 9px;
  height: 9px;
  flex: 0 0 9px;
  border-radius: 999px;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(0, 113, 227, 0.4);
}
.dot-line.done {
  background: var(--live);
  box-shadow: none;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.text.done {
  text-decoration: line-through;
  opacity: 0.5;
}
.sub {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-3);
  font-size: 0.78rem;
  white-space: nowrap;
}
.mini.ghost {
  min-width: 0;
  padding: 3px 8px;
  border: 0;
  border-radius: 8px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  transition: color 160ms ease;
}
.mini.ghost:hover {
  color: var(--heat);
}
</style>
