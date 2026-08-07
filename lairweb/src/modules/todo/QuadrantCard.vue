<script setup lang="ts">
// 四象限卡片（纯展示 + 勾选/删除）
import Tag from '../../components/Tag.vue'
import type { TodoItem } from './api'

defineProps<{ title: string; items: TodoItem[] }>()

const emit = defineEmits<{
  (e: 'toggle', item: TodoItem): void
  (e: 'remove', id: number): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>{{ title }}</span>
      <Tag variant="gray">{{ items.length }}</Tag>
    </div>
    <div class="row-list">
      <div v-for="item in items" :key="item.id" class="row">
        <span class="main" @click="emit('toggle', item)">
          <span class="check" :class="{ on: item.done }" aria-hidden="true">{{ item.done ? '✓' : '' }}</span>
          <span class="text" :class="{ done: item.done }">{{ item.text }}</span>
        </span>
        <span class="sub">
          <span class="due">{{ item.due }}</span>
          <button class="mini ghost" @click.stop="emit('remove', item.id)">✕</button>
        </span>
      </div>
      <p v-if="items.length === 0" class="empty">暂无任务</p>
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
.check {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--text-4);
  border-radius: 6px;
  font-size: 0.72rem;
  color: #fff;
  transition: border-color 160ms ease, background 160ms ease;
}
.check.on {
  border-color: var(--accent);
  background: var(--accent);
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
  gap: 8px;
}
.due {
  font-size: 0.78rem;
  color: var(--text-3);
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
.empty {
  margin: 6px 4px;
  color: var(--text-4);
  font-size: 0.84rem;
}
</style>
