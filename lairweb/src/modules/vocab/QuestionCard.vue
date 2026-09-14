<script setup lang="ts">
// 自测四选一：给出单词选正确释义；选错标红可继续选，是否一次选对决定评分
import { onMounted, ref } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { Volume2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { playWord } from './audio'
import type { QueueItem, VocabWord } from './api'

const props = defineProps<{ item: QueueItem; options: Array<{ word: VocabWord; correct: boolean }> }>()
const emit = defineEmits<{ done: [payload: { correct: boolean; wrongTimes: number; durationMs: number }] }>()

const pickedWrong = ref(new Set<number>())
const wrongTimes = ref(0)
const startedAt = Date.now()

// 数字键 1-4 直接选择（TypeWords 同款快捷键）
onKeyStroke(
  (e) => {
    const idx = ['1', '2', '3', '4'].indexOf(e.key)
    if (idx >= 0 && props.options[idx]) pick(props.options[idx])
  },
  { eventName: 'keydown' },
)

function meaningOf(option: { word: VocabWord }): string {
  const t = option.word.translations[0]
  return t ? `${t.pos} ${t.cn}` : '—'
}

function pick(option: { word: { id: number }; correct: boolean }) {
  if (option.correct) {
    emit('done', { correct: wrongTimes.value === 0, wrongTimes: wrongTimes.value, durationMs: Date.now() - startedAt })
    return
  }
  if (!pickedWrong.value.has(option.word.id)) {
    pickedWrong.value.add(option.word.id)
    wrongTimes.value += 1
  }
}

onMounted(() => playWord(props.item.word))
</script>

<template>
  <div class="question">
    <div class="word-head">
      <span class="q-word">{{ item.word }}</span>
      <Button
        variant="ghost"
        size="icon"
        class="rounded-full text-[var(--accent)] hover:bg-[rgba(var(--accent-rgb),0.08)] hover:text-[var(--accent)]"
        aria-label="播放发音"
        @click="playWord(item.word)"
      >
        <Volume2 class="size-5" />
      </Button>
    </div>
    <span v-if="item.phoneticUs || item.phoneticUk" class="q-phonetic">/{{ item.phoneticUs || item.phoneticUk }}/</span>

    <div class="options">
      <button
        v-for="(opt, i) in options"
        :key="opt.word.id"
        class="option-btn"
        :class="{ wrong: pickedWrong.has(opt.word.id) }"
        type="button"
        @click="pick(opt)"
      >
        <span class="opt-key">{{ i + 1 }}</span>
        {{ meaningOf(opt) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.question {
  background: var(--surface);
  border-radius: var(--r-panel);
  box-shadow: var(--sh-panel);
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.word-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.q-word {
  font-size: clamp(2rem, 5vw, 2.8rem);
  font-weight: 700;
}
.q-phonetic {
  color: var(--text-3);
}

.options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 640px;
  margin-top: 10px;
}
.option-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  background: transparent;
  text-align: left;
  font-size: 0.92rem;
  color: var(--text);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.option-btn:hover {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.04);
}
.option-btn.wrong {
  border-color: rgba(255, 59, 48, 0.5);
  background: rgba(255, 59, 48, 0.06);
  color: var(--text-3);
  text-decoration: line-through;
  pointer-events: none;
}
.option-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.opt-key {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.05);
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-3);
}
</style>
