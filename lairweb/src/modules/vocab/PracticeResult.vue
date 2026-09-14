<script setup lang="ts">
// 练习结束页：正确率 + 用时 + 每词下次复习时间，可再来一轮或返回词书
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import type { VocabSessionSummary } from './api'
import { VOCAB_MODES } from './api'
import StatStrip, { type StatItem } from './StatStrip.vue'

const props = defineProps<{
  summary: VocabSessionSummary
  /** 每个练过的词与下次复习时间 */
  words: Array<{ word: string; due: string | null; correct: boolean }>
}>()
const emit = defineEmits<{ restart: []; back: [] }>()

const modeLabel = computed(() => VOCAB_MODES.find((m) => m.value === props.summary.mode)?.label ?? props.summary.mode)
const accuracy = computed(() =>
  props.summary.totalCount ? Math.round((props.summary.correctCount / props.summary.totalCount) * 100) : 0,
)
const durationText = computed(() => {
  const s = props.summary.durationSec
  return s >= 60 ? `${Math.floor(s / 60)} 分 ${s % 60} 秒` : `${s} 秒`
})

/** 本次成绩：正确率 / 通过词数 / 用时（与词书页共用同一套统计排版） */
const statItems = computed<StatItem[]>(() => [
  { num: `${accuracy.value}%`, label: '正确率' },
  { num: `${props.summary.correctCount}/${props.summary.totalCount}`, label: '通过词数' },
  { num: durationText.value, label: '用时' },
])

function dueText(due: string | null): string {
  if (!due) return ''
  const days = Math.ceil((new Date(due).getTime() - Date.now()) / 86400000)
  if (days <= 0) return '今天'
  if (days === 1) return '明天'
  return `${days} 天后`
}
</script>

<template>
  <div class="result">
    <div class="result-card">
      <p class="result-title">{{ modeLabel }}完成 🎉</p>
      <StatStrip bare :items="statItems" />

      <ul v-if="words.length" class="word-list">
        <li v-for="(w, i) in words" :key="i">
          <span class="w-word" :class="{ miss: !w.correct }">{{ w.word }}</span>
          <span class="w-due">{{ dueText(w.due) }}</span>
        </li>
      </ul>

      <div class="result-actions">
        <Button class="rounded-full px-6 shadow-[var(--sh-cta)]" @click="emit('restart')">
          <RotateCcw class="size-4" />
          再来一轮
        </Button>
        <Button variant="outline" class="rounded-full px-6" @click="emit('back')">返回词书</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result {
  display: flex;
  justify-content: center;
  padding-top: 24px;
}
.result-card {
  width: min(560px, 100%);
  background: var(--surface);
  border-radius: var(--r-panel);
  box-shadow: var(--sh-panel);
  padding: 36px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.result-title {
  margin: 0;
  text-align: center;
  font-size: 1.2rem;
  font-weight: 700;
}

.word-list {
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 240px;
  overflow-y: auto;
  border-top: 1px solid var(--hairline);
}
.word-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 2px;
  border-bottom: 1px solid var(--hairline);
}
.w-word {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.w-word.miss {
  color: var(--destructive);
}
.w-due {
  font-size: 0.8rem;
  color: var(--text-3);
}

.result-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
