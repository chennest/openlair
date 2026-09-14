<script setup lang="ts">
// 统计条：词书主页 / 词书详情 / 练习结束页共用的「大数字 + 小标签」
// 数字走 .big-num（全站统一字号与 tabular-nums），标签 12px 灰阶
export interface StatItem {
  num: string | number
  label: string
  /** 仅「待复习」用 heat 强调；muted 用于零值/未学 */
  tone?: 'default' | 'heat' | 'muted'
}

withDefaults(defineProps<{ items: StatItem[]; bare?: boolean }>(), { bare: false })
</script>

<template>
  <div :class="bare ? 'stat-strip bare' : 'stat-strip'">
    <div v-for="it in items" :key="it.label" class="stat">
      <span class="big-num" :class="it.tone && it.tone !== 'default' ? it.tone : undefined">{{ it.num }}</span>
      <span class="label">{{ it.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.stat-strip {
  display: flex;
  gap: 8px;
  padding: 14px 20px;
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-card);
}
/* 嵌在已有面板内部时：不再自带白底/阴影/内边距 */
.stat-strip.bare {
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.stat {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat + .stat {
  border-left: 1px solid var(--hairline);
}
.stat-strip.bare .stat + .stat {
  border-left: 0;
}

.label {
  font-size: 0.72rem;
  color: var(--text-3);
  white-space: nowrap;
}
.big-num.heat {
  color: var(--heat);
}
.big-num.muted {
  color: var(--text-3);
}

@media (max-width: 680px) {
  .stat-strip {
    flex-wrap: wrap;
    gap: 12px 0;
  }
  .stat {
    flex: 0 0 33.33%;
  }
  .stat + .stat {
    border-left: 0;
  }
}
</style>
