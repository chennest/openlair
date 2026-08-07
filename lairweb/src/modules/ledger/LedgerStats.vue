<script setup lang="ts">
// 支出分类统计：灰轨道 + 单强调色占比条（design-system.md：meter 灰轨道 + accent 填充）
import type { CategoryStat } from './api'

defineProps<{ stats: CategoryStat[] }>()
</script>

<template>
  <article class="card">
    <div class="card-title"><span>支出分类统计</span></div>
    <div v-if="stats.length === 0" class="empty">暂无支出数据</div>
    <div class="stat-list">
      <div v-for="s in stats" :key="s.categoryId" class="stat">
        <div class="stat-top">
          <span class="name">{{ s.name }}</span>
          <span class="val num">¥{{ Number(s.amount).toFixed(0) }} · {{ s.percent }}%</span>
        </div>
        <div class="meter">
          <i :style="{ width: s.percent + '%' }"></i>
        </div>
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
  margin-bottom: 16px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.empty {
  padding: 20px 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.84rem;
}
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.stat-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.name {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text);
}
.val {
  font-size: 0.78rem;
  color: var(--text-3);
}
.meter {
  height: 6px;
  border-radius: var(--r-pill);
  background: var(--track);
  overflow: hidden;
}
.meter i {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--accent);
  transition: width 400ms var(--ease-out-quart);
}
</style>
