<script setup lang="ts">
// 答词后的复习面板：单词 + 音标 + 释义 + 例句（可发音），展示下次复习时间
import { computed, onMounted } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { Volume2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { playSentence, playWord } from './audio'
import { masteryText, tone } from './status'
import type { QueueItem, VocabProgress, VocabWord } from './api'

const props = defineProps<{
  item: QueueItem
  correct: boolean
  /** 作答响应里带回来的下次到期时间（没掌握的词一律压到次日） */
  due: string | null
  /** 作答响应里带回来的最新进度：用来显示「还差 N 次答对」 */
  progress: VocabProgress | null
  /** 跟打四选一的作答项：回显「你选的是 X → 对应英语」；其余模式为 null */
  picked?: { word: VocabWord; correct: boolean } | null
}>()
const emit = defineEmits<{ continue: [] }>()

const firstSentence = computed(() => props.item.sentences[0] ?? null)
const mastery = computed(() => masteryText(props.progress))

/** 选中项的中文释义（只取首义，与选项按钮上的字一致） */
const pickedMeaning = computed(() => {
  const t = props.picked?.word.translations[0]
  return t ? `${t.pos} ${t.cn}` : ''
})

/** 选中那个英文词的全部词性释义：错选时要说清"它自己是什么意思" */
const pickedSenses = computed(() =>
  (props.picked?.word.translations ?? []).map((t) => `${t.pos} ${t.cn}`).join(' / '),
)

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
    <div class="reveal" @click.stop>
      <Badge variant="ghost" class="self-start" :class="tone(correct ? 'green' : 'red')">
        {{ correct ? '✓ 通过' : '✗ 再练' }}
      </Badge>
      <div class="reveal-word">
        <h3>{{ item.word }}</h3>
        <Button
          v-if="item.phoneticUs || item.phoneticUk"
          variant="ghost"
          size="icon-sm"
          class="rounded-full text-[var(--accent)] hover:bg-[rgba(var(--accent-rgb),0.08)] hover:text-[var(--accent)]"
          aria-label="播放单词"
          @click="playWord(item.word)"
        >
          <Volume2 class="size-4" />
        </Button>
      </div>
      <span v-if="item.phoneticUs || item.phoneticUk" class="phonetic">/{{ item.phoneticUs || item.phoneticUk }}/</span>

      <!-- 跟打四选一：先给「选对没选对」的判定，再把「你选的中文 → 那个英语词」摊开，
           并列出那个英语词自己的全部释义（选对时就是题面词，跟下方 .meanings 会有重复，
           但这是刻意保留的：让人在同一块里就能把「我选的中文 = 哪个英文 = 它还有什么意思」看完） -->
      <div v-if="picked" class="pick-note" :class="{ bad: !picked.correct }">
        <span class="pick-mark">{{ picked.correct ? '✓ 选对了' : '✗ 选错了' }}</span>
        <p class="pick-line">
          你选的是 <b>{{ pickedMeaning }}</b>
          <span class="pick-arrow">→</span>
          <b class="pick-word">{{ picked.word.word }}</b>
        </p>
        <p class="pick-senses">
          {{ picked.word.word }}：{{ pickedSenses }}
        </p>
      </div>

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
        <div class="foot-meta">
          <span class="due">{{ dueText ?? '' }}</span>
          <span v-if="mastery" class="mastery" :class="{ done: progress?.status === 'mastered' }">{{ mastery }}</span>
        </div>
        <Button class="rounded-full px-6 shadow-[var(--sh-cta)]" @click="emit('continue')">
          继续 ⏎
        </Button>
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
.phonetic {
  color: var(--text-3);
  font-size: 0.92rem;
}

/* 跟打四选一的作答回显：中性底，错选转暖红；比正文低一档，不跟释义抢视线 */
.pick-note {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: var(--r-thumb);
  background: rgba(0, 0, 0, 0.03);
}
.pick-note.bad {
  background: rgba(255, 59, 48, 0.06);
}
.pick-mark {
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--live);
}
.pick-note.bad .pick-mark {
  color: var(--destructive);
}
.pick-line {
  margin: 0;
  color: var(--text-2);
  font-size: 0.85rem;
  line-height: 1.5;
}
.pick-line b {
  color: var(--text);
  font-weight: 600;
}
.pick-arrow {
  margin: 0 6px;
  color: var(--text-3);
}
.pick-word {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
}
.pick-senses {
  margin: 0;
  color: var(--text-3);
  font-size: 0.8rem;
  line-height: 1.5;
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
  gap: 12px;
  margin-top: 6px;
}
.foot-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.due {
  font-size: 0.8rem;
  color: var(--text-3);
}
/* 掌握进度：还差 N 次时走次级色，已记住转绿（与 statusMeta 的 green 同源语义） */
.mastery {
  font-size: 0.76rem;
  color: var(--text-4);
}
.mastery.done {
  color: #0a5a2c;
  font-weight: 600;
}
</style>
