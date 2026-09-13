<script setup lang="ts">
// 答词后的复习面板：单词 + 音标 + 释义 + 例句（可发音），展示下次复习时间
import { computed, onMounted } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { Volume2 } from '@lucide/vue'
import { playSentence, playWord } from './audio'
import type { QueueItem } from './api'

const props = defineProps<{
  item: QueueItem
  correct: boolean
  /** 作答响应里带回来的下次到期时间（新答错的词约 1 天后） */
  due: string | null
}>()
const emit = defineEmits<{ continue: [] }>()

const firstSentence = computed(() => props.item.sentences[0] ?? null)

const dueText = computed(() => {
  if (!props.due) return null
  const d = new Date(props.due)
  const days = Math.ceil((d.getTime() - Date.now()) / 86400000)
  if (days <= 0) return '今天将再次出现'
  if (days === 1) return '明天复习'
  return `${days} 天后复习`
})

onKeyStroke('Enter', (e) => {
  e.preventDefault()
  emit('continue')
}, { eventName: 'keydown' })
onMounted(() => {
  if (firstSentence.value) playSentence(firstSentence.value.en)
})
</script>

<template>
  <div class="reveal-mask" @click="emit('continue')">
    <div class="reveal" :class="{ bad: !correct }" @click.stop>
      <span class="verdict" :class="correct ? 'ok' : 'no'">{{ correct ? '✓ 通过' : '✗ 再练' }}</span>
      <div class="reveal-word">
        <h3>{{ item.word }}</h3>
        <button v-if="item.phoneticUs || item.phoneticUk" class="sound-btn" type="button" aria-label="播放单词" @click="playWord(item.word)">
          <Volume2 class="size-4" />
        </button>
      </div>
      <span v-if="item.phoneticUs || item.phoneticUk" class="phonetic">/{{ item.phoneticUs || item.phoneticUk }}/</span>

      <ul class="meanings">
        <li v-for="(t, i) in item.translations" :key="i">
          <b>{{ t.pos }}</b>
          {{ t.cn }}
        </li>
      </ul>

      <div v-if="firstSentence" class="sentence">
        <p class="en">{{ firstSentence.en }}</p>
        <p class="cn">{{ firstSentence.cn }}</p>
      </div>

      <div class="reveal-foot">
        <span class="due">{{ dueText ?? '' }}</span>
        <button class="continue-btn" type="button" @click="emit('continue')">继续 ⏎</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reveal-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.32);
  padding: 20px;
}
.reveal {
  width: min(520px, 100%);
  background: var(--surface);
  border-radius: var(--r-panel);
  box-shadow: var(--sh-overlay);
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.verdict {
  align-self: flex-start;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 999px;
}
.verdict.ok {
  color: var(--live);
  background: rgba(48, 209, 88, 0.12);
}
.verdict.no {
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.1);
}

.reveal-word {
  display: flex;
  align-items: center;
  gap: 12px;
}
.reveal-word h3 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
}
.sound-btn {
  display: inline-flex;
  padding: 8px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
}
.sound-btn:hover {
  background: rgba(0, 113, 227, 0.08);
}
.phonetic {
  color: var(--text-3);
  font-size: 0.92rem;
}

.meanings {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--text);
  font-size: 0.95rem;
}
.meanings b {
  color: var(--text-3);
  font-weight: 600;
  margin-right: 4px;
}

.sentence {
  border-top: 1px solid var(--hairline);
  padding-top: 12px;
  cursor: pointer;
}
.sentence .en {
  margin: 0;
  font-size: 0.92rem;
  color: var(--text);
}
.sentence .cn {
  margin: 4px 0 0;
  font-size: 0.84rem;
  color: var(--text-3);
}

.reveal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}
.due {
  font-size: 0.8rem;
  color: var(--text-3);
}
.continue-btn {
  padding: 9px 22px;
  border: none;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--sh-cta);
}
.continue-btn:hover {
  filter: brightness(1.05);
}
</style>
