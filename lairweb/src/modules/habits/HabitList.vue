<script setup lang="ts">
// 习惯列表（纯展示 + 打卡/删除）
import type { Habit } from './api'

defineProps<{ habits: Habit[] }>()

const emit = defineEmits<{
  (e: 'toggle', habit: Habit): void
  (e: 'remove', id: string): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>习惯打卡</span>
      <span class="tag green">{{ habits.length }} 项</span>
    </div>
    <div class="row-list">
      <div v-for="h in habits" :key="h.id" class="row habit-row">
        <span class="main">
          <span class="streak">🔥 {{ h.streak }}</span>
          <span class="text">{{ h.name }}</span>
        </span>
        <span class="week-dots" aria-label="最近七天">
          <span v-for="(d, i) in h.week" :key="i" class="day-dot" :class="{ on: d }"></span>
        </span>
        <button class="mini gold" @click="emit('toggle', h)">{{ h.done ? '取消' : '打卡' }}</button>
        <button class="mini ghost" @click="emit('remove', h.id)">✕</button>
      </div>
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
.tag {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #0e1f16;
  background: #8ee6a5;
}
.row-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 4px;
  border-bottom: 1px solid rgba(242, 234, 223, 0.06);
  font-size: 0.9rem;
}
.row:last-child {
  border-bottom: 0;
}
.habit-row {
  padding: 12px 4px;
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.streak {
  color: #f6d37a;
  font-weight: 800;
  font-size: 0.86rem;
  flex: 0 0 auto;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.week-dots {
  display: flex;
  gap: 5px;
  align-items: center;
  flex: 0 0 auto;
}
.day-dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  background: rgba(242, 234, 223, 0.1);
  transition: background 160ms ease;
}
.day-dot.on {
  background: #8ee6a5;
  box-shadow: 0 0 8px rgba(142, 230, 165, 0.45);
}
.mini {
  min-width: 0;
  padding: 6px 12px;
  border-radius: 10px;
  border: 0;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}
.mini.gold {
  color: #14120f;
  background: #f6d37a;
}
.mini.ghost {
  color: rgba(242, 234, 223, 0.6);
  background: transparent;
}
.mini.ghost:hover {
  color: #ffac8b;
}
</style>
