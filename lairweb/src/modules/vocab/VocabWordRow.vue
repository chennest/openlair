<script setup lang="ts">
// 生词列表行（错词本 / 收藏共用）：发音 + 释义 + 行内操作
// 行本身不带卡片外观 —— 由父级一个面板 + hairline 分割承载（统一表面 > 碎片化卡片）
import { computed } from 'vue'
import { Volume2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { playWord } from './audio'
import { MASTER_LABEL, masteryText, reviewDueText, wordMeaning } from './status'
import type { QueueItem } from './api'

const props = defineProps<{
  item: QueueItem
  /** tab 来源：wrong 显示移出错词本/标记记住，collect 显示取消收藏 */
  source: 'wrong' | 'collect'
}>()
const emit = defineEmits<{
  dismissWrong: [wordId: number]
  master: [wordId: number]
  uncollect: [wordId: number]
}>()

const meaning = computed(() => wordMeaning(props.item.translations))
const dueText = computed(() => reviewDueText(props.item.progress?.due))
/** 掌握进度：已连对 N/M · 还差 K 次（未做过识词判断的词为空串） */
const mastery = computed(() => masteryText(props.item.progress))
</script>

<template>
  <div class="row">
    <Button
      variant="ghost"
      size="icon-sm"
      class="rounded-full text-[var(--accent)] hover:bg-[rgba(var(--accent-rgb),0.08)] hover:text-[var(--accent)]"
      aria-label="播放发音"
      @click="playWord(item.word)"
    >
      <Volume2 class="size-4" />
    </Button>

    <div class="word-main">
      <div class="word-line">
        <span class="w">{{ item.word }}</span>
        <span v-if="item.phoneticUs || item.phoneticUk" class="p">/{{ item.phoneticUs || item.phoneticUk }}/</span>
        <span v-if="dueText" class="due">{{ dueText }}</span>
        <span
          v-if="mastery"
          class="mastery"
          :class="{ done: item.progress?.status === 'mastered' }"
        >{{ mastery }}</span>
      </div>
      <p class="m">{{ meaning }}</p>
    </div>

    <div class="actions">
      <Button
        v-if="source === 'wrong'"
        variant="ghost"
        size="sm"
        class="rounded-full text-[var(--text-2)]"
        @click="emit('dismissWrong', item.id)"
      >移出错词本</Button>
      <Button
        v-if="source === 'wrong'"
        variant="outline"
        size="sm"
        class="rounded-full"
        @click="emit('master', item.id)"
      >{{ MASTER_LABEL }}</Button>
      <Button
        v-if="source === 'collect'"
        variant="ghost"
        size="sm"
        class="rounded-full text-[var(--text-2)]"
        @click="emit('uncollect', item.id)"
      >取消收藏</Button>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--hairline);
  transition: background 150ms ease;
}
.row:last-child {
  border-bottom: 0;
}
.row:hover {
  background: var(--hover);
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
/* 掌握进度：灰色 trailing 提示，已记住转绿（与 statusMeta 的 green 同源） */
.mastery {
  font-size: 0.72rem;
  color: var(--text-4);
}
.mastery.done {
  color: #0a5a2c;
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

@media (max-width: 680px) {
  .row {
    flex-wrap: wrap;
  }
  .actions {
    width: 100%;
    padding-left: 44px;
  }
}
</style>
