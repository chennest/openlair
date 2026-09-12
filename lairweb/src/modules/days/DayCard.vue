<script setup lang="ts">
// 倒数日卡片：纯展示组件（props 进 / emit 出），状态配色见下方注释
import { computed } from 'vue'
import { Pin } from '@lucide/vue'
import type { DayItem } from './api'

const props = defineProps<{ day: DayItem }>()
const emit = defineEmits<{ (e: 'edit', id: number): void }>()

const REPEAT_LABEL: Record<DayItem['repeat'], string> = { once: '一次性', yearly: '每年', monthly: '每月' }

// ── emoji 底色：按 emoji 码点稳定取色（Apple 语义色浅底） ──
const TINTS = [
  'rgba(0, 113, 227, 0.10)',   // 蓝
  'rgba(255, 107, 0, 0.12)',   // 橙
  'rgba(255, 55, 95, 0.10)',   // 粉
  'rgba(48, 209, 88, 0.14)',   // 绿
  'rgba(94, 92, 230, 0.12)',   // 靛
  'rgba(255, 204, 0, 0.20)',   // 黄
]
const tint = computed(() => {
  const cp = [...props.day.emoji].reduce((s, ch) => s + ch.codePointAt(0)!, 0)
  return TINTS[cp % TINTS.length]
})

/** 日期行右侧补充：每月 → 「每月N日」，其余 → 重复规则名 */
const dateTail = computed(() => {
  if (props.day.repeat === 'monthly') return `每月${Number(props.day.date.slice(8, 10))}日`
  return REPEAT_LABEL[props.day.repeat]
})

const dateLabel = computed(() => {
  const [y, m, d] = props.day.date.split('-').map(Number)
  return `${y}年${m}月${d}日`
})
</script>

<template>
  <article
    class="day-card"
    :class="{ 'is-pinned': day.pinned }"
    role="button"
    tabindex="0"
    @click="emit('edit', day.id)"
    @keyup.enter="emit('edit', day.id)"
  >
    <div class="card-top">
      <span class="emoji-tile" :style="{ background: tint }">{{ day.emoji }}</span>
      <div class="card-meta">
        <Pin v-if="day.pinned" class="pin" :size="15" aria-label="已置顶" />
        <span class="chip" :class="day.repeat">{{ REPEAT_LABEL[day.repeat] }}</span>
      </div>
    </div>

    <h3 class="card-title">{{ day.title }}</h3>

    <div class="card-num">
      <template v-if="day.daysUntil === 0">
        <span class="num-today"><span class="live-dot" aria-hidden="true"></span>就是今天</span>
      </template>
      <template v-else>
        <span class="num" :class="{ urgent: day.daysUntil > 0 && day.daysUntil <= 7, past: day.daysUntil < 0 }">
          {{ Math.abs(day.daysUntil) }}
        </span>
        <span class="num-unit">
          {{ day.daysUntil < 0 ? '天啦' : day.repeat === 'yearly' && (day.milestone ?? 0) > 1 ? `天后 · 第${day.milestone}次` : '天后' }}
        </span>
      </template>
    </div>

    <div class="card-date">
      <span class="d">{{ dateLabel }}</span>
      <span>{{ dateTail }}</span>
    </div>
  </article>
</template>

<style scoped>
.day-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 20px 18px;
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-card);
  cursor: pointer;
  transition: transform 200ms var(--ease-out-quart), box-shadow 200ms var(--ease-out-quart);
}
.day-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--sh-lift);
}
.day-card:focus-visible {
  outline: none;
  box-shadow: var(--sh-card), 0 0 0 3px rgba(var(--accent-rgb), 0.35);
}
.day-card.is-pinned {
  box-shadow: var(--sh-card), 0 0 0 1.5px rgba(var(--accent-rgb), 0.3);
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.emoji-tile {
  flex: 0 0 46px;
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: var(--r-thumb);
  font-size: 1.5rem;
  line-height: 1;
}
.card-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pin {
  color: var(--accent);
}
.chip {
  padding: 3px 9px;
  border-radius: var(--r-pill);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text-3);
  background: rgba(0, 0, 0, 0.055);
}
.chip.yearly {
  color: var(--accent);
  background: rgba(var(--accent-rgb), 0.1);
}
.chip.monthly {
  color: var(--indigo);
  background: rgba(94, 92, 230, 0.1);
}

.card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.card-num {
  margin-top: auto;
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.num {
  font-size: 56px;
  font-weight: 250;
  line-height: 1;
  letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}
/* 临近（≤7 天）橙色预警 */
.num.urgent {
  color: var(--heat);
  font-weight: 350;
}
/* 已过累计（纪念日）靛蓝 */
.num.past {
  color: var(--indigo);
}
.num-unit {
  color: var(--text-3);
  font-size: 0.95rem;
  font-weight: 600;
}
.num-today {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--live);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--live);
  box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.5);
  animation: pulse-dot 2.2s infinite;
}
@keyframes pulse-dot {
  0%   { box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.5); }
  70%  { box-shadow: 0 0 0 7px rgba(48, 209, 88, 0); }
  100% { box-shadow: 0 0 0 0 rgba(48, 209, 88, 0); }
}

.card-date {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-3);
  font-size: 0.78rem;
}
.card-date .d {
  font-variant-numeric: tabular-nums;
}

@media (prefers-reduced-motion: reduce) {
  .day-card { transition: none; }
  .live-dot { animation: none; }
}
</style>
