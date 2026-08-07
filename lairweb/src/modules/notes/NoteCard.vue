<script setup lang="ts">
// 笔记卡片（纯展示 + 删除）
defineProps<{
  title: string
  summary: string
  tags: string[]
  updatedAt: string
}>()

const emit = defineEmits<{
  (e: 'remove'): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>{{ updatedAt }}</span>
      <span class="more" @click="emit('remove')">删除 ✕</span>
    </div>
    <h3 class="note-title">{{ title }}</h3>
    <p class="hint">{{ summary }}</p>
    <div class="tag-row">
      <span v-for="tag in tags" :key="tag" class="tag gray"># {{ tag }}</span>
    </div>
  </article>
</template>

<style scoped>
.card {
  padding: 22px 22px 20px;
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-card);
  transition: transform 200ms var(--ease-out-quart), box-shadow 200ms var(--ease-out-quart);
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--sh-lift);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  color: var(--text-3);
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.more {
  color: var(--text-3);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 160ms ease;
}
.more:hover {
  color: var(--heat);
}
.note-title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.hint {
  margin: 0;
  color: var(--text-2);
  font-size: 0.82rem;
  line-height: 1.6;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}
.tag {
  flex: 0 0 auto;
  padding: 3px 10px;
  border-radius: var(--r-pill);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.05);
}
</style>
