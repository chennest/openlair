<script setup lang="ts">
// 生词列表行（错词本 / 收藏共用）：发音 + 释义 + 上下文操作按钮
import { computed } from 'vue'
import { Volume2 } from '@lucide/vue'
import { playWord } from './audio'
import type { QueueItem } from './api'

const props = defineProps<{
  item: QueueItem
  /** tab 来源：wrong 显示移出错词本/已掌握，collect 显示取消收藏 */
  source: 'wrong' | 'collect'
}>()
const emit = defineEmits<{
  dismissWrong: [wordId: number]
  master: [wordId: number]
  uncollect: [wordId: number]
}>()

const meaning = computed(() =>
  props.item.translations
    .slice(0, 2)
    .map((t) => `${t.pos} ${t.cn}`)
    .join('；'),
)
const dueText = computed(() => {
  const due = props.item.progress?.due
  if (!due) return ''
  const days = Math.ceil((new Date(due).getTime() - Date.now()) / 86400000)
  if (days <= 0) return '待复习'
  if (days === 1) return '明天复习'
  return `${days} 天后复习`
})
</script>

<template>
  <div class="word-row">
    <button class="sound" type="button" aria-label="播放发音" @click="playWord(item.word)">
      <Volume2 class="size-4" />
    </button>
    <div class="word-main">
      <div class="word-line">
        <span class="w">{{ item.word }}</span>
        <span v-if="item.phoneticUs || item.phoneticUk" class="p">/{{ item.phoneticUs || item.phoneticUk }}/</span>
        <span v-if="dueText" class="due">{{ dueText }}</span>
      </div>
      <p class="m">{{ meaning }}</p>
    </div>
    <div class="actions">
      <button
        v-if="source === 'wrong'"
        class="act-btn"
        type="button"
        @click="emit('dismissWrong', item.id)"
      >移出错词本</button>
      <button
        v-if="source === 'wrong'"
        class="act-btn"
        type="button"
        @click="emit('master', item.id)"
      >已掌握</button>
      <button
        v-if="source === 'collect'"
        class="act-btn"
        type="button"
        @click="emit('uncollect', item.id)"
      >取消收藏</button>
    </div>
  </div>
</template>

<style scoped>
.word-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: var(--surface);
  border-radius: var(--r-thumb);
  box-shadow: var(--sh-card);
}
.sound {
  flex: none;
  display: inline-flex;
  padding: 8px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
}
.sound:hover {
  background: rgba(0, 113, 227, 0.08);
}
.word-main {
  flex: 1;
  min-width: 0;
}
.word-line {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.w {
  font-weight: 700;
  font-size: 1rem;
}
.p {
  color: var(--text-3);
  font-size: 0.8rem;
}
.due {
  font-size: 0.72rem;
  color: var(--heat);
  font-weight: 600;
}
.m {
  margin: 3px 0 0;
  color: var(--text-2);
  font-size: 0.84rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actions {
  flex: none;
  display: flex;
  gap: 8px;
}
.act-btn {
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  padding: 7px 13px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-2);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.act-btn:hover {
  background: rgba(0, 0, 0, 0.04);
}
.act-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
