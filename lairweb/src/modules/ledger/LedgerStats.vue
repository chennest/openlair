<script setup lang="ts">
// 支出分类统计列表（纯展示）
import type { CategoryStat } from './api'

defineProps<{ stats: CategoryStat[] }>()
</script>

<template>
  <article class="card">
    <div class="card-title"><span>支出分类统计</span></div>
    <div class="row-list">
      <div v-for="item in stats" :key="item.name" class="row">
        <span class="main text">{{ item.name }}</span>
        <span class="sub">¥{{ Number(item.amount).toFixed(0) }} · {{ item.percent }}%</span>
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
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub {
  color: rgba(242, 234, 223, 0.45);
  font-size: 0.78rem;
}
</style>
