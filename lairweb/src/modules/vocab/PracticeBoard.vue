<script setup lang="ts">
// 打字练习核心组件（跟打/听写/默写共用）：窗口级键盘捕获，逐字判分
// - 跟打：单词可见；听写：只放发音；默写：只给中文释义
// - 打错不前进只计数，全部打完自动提交
import { computed, onMounted, ref } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { RotateCcw, Volume2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { playWord } from './audio'
import type { QueueItem, VocabMode } from './api'

const props = defineProps<{ item: QueueItem; mode: Exclude<VocabMode, 'self_test'> }>()
const emit = defineEmits<{ done: [payload: { correct: boolean; wrongTimes: number; durationMs: number }] }>()

const target = computed(() => props.item.word)
const chars = computed(() => target.value.split(''))
const typedCount = ref(0)
const wrongTimes = ref(0)
const flash = ref(false)
const ukAccent = ref(false) // 发音口音：默认美音，可切英音
const startedAt = Date.now()

const showWord = computed(() => props.mode === 'follow')
const showPhonetic = computed(() => props.mode === 'follow')

function replay() {
  playWord(target.value, ukAccent.value)
}

function finish(correct: boolean) {
  emit('done', { correct, wrongTimes: wrongTimes.value, durationMs: Date.now() - startedAt })
}

onKeyStroke(
  (e) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      replay()
      return
    }
    if (e.key === 'Escape') {
      finish(false)
      return
    }
    if (e.key.length !== 1) return
    e.preventDefault()
    if (typedCount.value >= chars.value.length) return
    if (e.key === target.value[typedCount.value]) {
      typedCount.value += 1
      if (typedCount.value === chars.value.length) finish(true)
    } else {
      wrongTimes.value += 1
      flash.value = true
      setTimeout(() => (flash.value = false), 180)
    }
  },
  { eventName: 'keydown' },
)

onMounted(() => {
  // 跟打/听写进词即发音；默写只见释义不剧透发音
  if (props.mode !== 'spell') replay()
})
</script>

<template>
  <div class="board">
    <!-- 题面：单词（跟打可见）或遮罩（听写/默写） -->
    <div class="word-line" :class="{ masked: !showWord }" aria-label="typing target">
      <span
        v-for="(ch, i) in chars"
        :key="i"
        class="ch"
        :class="{
          typed: i < typedCount,
          cursor: i === typedCount,
          miss: !showWord && i === typedCount && flash,
        }"
      >{{ showWord ? ch : '•' }}</span>
    </div>

    <div class="meta-line">
      <span v-if="showPhonetic && (item.phoneticUs || item.phoneticUk)" class="phonetic">/{{ item.phoneticUs || item.phoneticUk }}/</span>
      <span class="wrong-hint" :class="{ shake: flash }">错 {{ wrongTimes }}</span>
    </div>

    <!-- 释义提示（听写/默写的解题线索） -->
    <p class="meaning">{{ item.translations.map((t) => `${t.pos} ${t.cn}`).join('；') }}</p>

    <div class="board-actions">
      <Button variant="outline" size="sm" class="rounded-full text-[var(--text-2)]" @click="replay">
        <Volume2 class="size-4" />
        发音（Tab）
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="rounded-full text-[var(--text-2)]"
        :title="ukAccent ? '切换为美音' : '切换为英音'"
        @click="ukAccent = !ukAccent; replay()"
      >
        {{ ukAccent ? '英音' : '美音' }}
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="rounded-full text-[var(--text-2)]"
        @click="typedCount = 0; wrongTimes = 0"
      >
        <RotateCcw class="size-4" />
        重打
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="rounded-full text-[var(--text-2)] hover:bg-[rgba(255,59,48,0.08)] hover:text-[var(--destructive)]"
        @click="finish(false)"
      >
        跳过（Esc）
      </Button>
    </div>
  </div>
</template>

<style scoped>
.board {
  background: var(--surface);
  border-radius: var(--r-panel);
  box-shadow: var(--sh-panel);
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.word-line {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: clamp(2rem, 6vw, 3.2rem);
  font-weight: 700;
  letter-spacing: 0.04em;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}
.ch {
  min-width: 0.62em;
  color: var(--text-3);
  transition: color 0.12s;
}
.ch.typed {
  color: var(--accent);
}
.ch.cursor {
  border-bottom: 3px solid var(--accent);
}
.ch.miss {
  color: var(--heat);
  transform: translateY(2px);
}
.word-line.masked .ch {
  color: rgba(0, 0, 0, 0.18);
}

.meta-line {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 1.4em;
}
.phonetic {
  color: var(--text-3);
  font-size: 1rem;
}
.wrong-hint {
  font-size: 0.8rem;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.wrong-hint.shake {
  color: var(--heat);
  font-weight: 700;
}

.meaning {
  margin: 0;
  max-width: 560px;
  text-align: center;
  color: var(--text-2);
  font-size: 0.95rem;
  line-height: 1.6;
}

.board-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}
</style>
