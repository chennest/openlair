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
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 22px;
  background: rgba(25, 22, 17, 0.66);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  color: rgba(242, 234, 223, 0.72);
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}
.more {
  color: rgba(242, 234, 223, 0.4);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: none;
  letter-spacing: 0;
  cursor: pointer;
}
.more:hover {
  color: #ffac8b;
}
.note-title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
}
.hint {
  margin: 0;
  color: rgba(242, 234, 223, 0.5);
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
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: rgba(242, 234, 223, 0.7);
  background: rgba(255, 255, 255, 0.08);
}
</style>
