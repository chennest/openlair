<script setup lang="ts">
// 四象限卡片（纯展示 + 勾选/删除）
import Tag from '../../components/Tag.vue'
import type { TodoItem } from './api'

defineProps<{ title: string; items: TodoItem[] }>()

const emit = defineEmits<{
  (e: 'toggle', item: TodoItem): void
  (e: 'remove', id: string): void
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
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.66);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: rgba(242, 234, 223, 0.72);
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
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
  border-bottom: 1px solid rgba(242, 234, 223, 0.06);
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
  border: 1.5px solid rgba(242, 234, 223, 0.3);
  border-radius: 6px;
  font-size: 0.72rem;
  color: #14120f;
}
.check.on {
  border-color: #8ee6a5;
  background: #8ee6a5;
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
  color: rgba(242, 234, 223, 0.45);
}
.mini.ghost {
  min-width: 0;
  padding: 3px 8px;
  border: 0;
  border-radius: 8px;
  color: rgba(242, 234, 223, 0.5);
  background: transparent;
  cursor: pointer;
}
.mini.ghost:hover {
  color: #ffac8b;
}
.empty {
  margin: 6px 4px;
  color: rgba(242, 234, 223, 0.32);
  font-size: 0.84rem;
}
</style>
