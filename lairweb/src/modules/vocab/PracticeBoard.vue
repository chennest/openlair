<script setup lang="ts">
// 打字练习核心组件（跟打/听写/默写共用）：窗口级键盘捕获，逐字判分
// - 跟打：单词可见；释义**不再直显**，改为 A/B/C/D 四选一作答（见 quiz）
// - 听写：只放发音；默写：只给中文释义（释义就是题面，不能藏）
// - 打错不前进只计数。跟打要「拼完 + 选对释义」两件事都做完才交卷，其余模式拼完即交卷。
import { computed, onMounted, ref } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { RotateCcw, Volume2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { playWord } from './audio'
import type { QueueItem, VocabMode, VocabWord } from './api'

const props = defineProps<{
  item: QueueItem
  mode: Exclude<VocabMode, 'self_test'>
  /** 释义四选一选项（跟打用，1 正确 + N 干扰）；少于 2 项就退回直显释义 */
  options: Array<{ word: VocabWord; correct: boolean }>
}>()
const emit = defineEmits<{
  done: [
    payload: {
      correct: boolean
      wrongTimes: number
      durationMs: number
      /** 跟打四选一的作答项（其余模式为 null）：结果面板要靠它回显「你选的是 X → 对应英语」 */
      picked: { word: VocabWord; correct: boolean } | null
    },
  ]
}>()

const target = computed(() => props.item.word)
const chars = computed(() => target.value.split(''))
const typedCount = ref(0)
const wrongTimes = ref(0)
const flash = ref(false)
const ukAccent = ref(false) // 发音口音：默认美音，可切英音
const startedAt = Date.now()

const showWord = computed(() => props.mode === 'follow')
const showPhonetic = computed(() => props.mode === 'follow')

/**
 * 跟打是否走「释义四选一」。
 * 选项不足 2 个（词池挑不出干扰项）时不强行出题 —— 只有一个选项的"选择题"是耍人，
 * 不如老实把释义直显出来。
 */
const quiz = computed(() => props.mode === 'follow' && props.options.length >= 2)
/** 拼写是否已完成 */
const spelled = computed(() => typedCount.value >= chars.value.length)
/**
 * 已作答的选项（跟打四选一**只给一次机会**）：
 * 选中即判定，不再改选 —— 错的那项既要标红，也要把正确项点亮给他看，
 * 让人当场就明白"我错在哪、对的又是哪个"，而不是靠一个个试出来。
 */
const answer = ref<{ word: VocabWord; correct: boolean } | null>(null)

/** 交卷条件：拼完 + （非四选一 或 已作答）。两件事谁先做完都行，齐了立刻判。 */
const canSubmit = computed(() => spelled.value && (!quiz.value || answer.value !== null))

const quizHint = computed(() => {
  const a = answer.value
  if (a) {
    if (a.correct) return '选对了 · 拼完这个词就交卷'
    // 错了就说清那一项其实是哪个词的释义 —— 干扰项本身也是个该认的词
    return `选错了 ·「${meaningOf(a.word)}」是 ${a.word.word} 的释义`
  }
  if (spelled.value) return '拼写完成 · 选出正确释义'
  return '这个词的释义是哪个？先选也行，边打边选都行'
})

function replay() {
  playWord(target.value, ukAccent.value)
}

function finish(correct: boolean) {
  emit('done', {
    correct,
    wrongTimes: wrongTimes.value,
    durationMs: Date.now() - startedAt,
    picked: answer.value,
  })
}

/** 两个条件都满足才自动交卷；不满足就静静等另一半做完 */
function trySubmit() {
  if (canSubmit.value) finish(true)
}

function meaningOf(word: VocabWord): string {
  const t = word.translations[0]
  return t ? `${t.pos} ${t.cn}` : '—'
}

/** 选项态：答错的那项标红，同时把正确项点亮（错了也要让人当场看见对的） */
const isWrongPick = (id: number) =>
  answer.value !== null && !answer.value.correct && answer.value.word.id === id
const isCorrectPick = (opt: { correct: boolean }) => answer.value !== null && opt.correct

function pick(option: { word: VocabWord; correct: boolean }) {
  if (answer.value) return // 已作答，锁定（四选一只给一次机会）
  answer.value = { word: option.word, correct: option.correct }
  if (!option.correct) {
    // 选错记一次错：交卷前提是零错，所以乱点没便宜可占
    wrongTimes.value += 1
    flash.value = true
    setTimeout(() => (flash.value = false), 180)
  }
  trySubmit()
}

/** 重打：拼写与作答一起归零，整词重来 */
function reset() {
  typedCount.value = 0
  wrongTimes.value = 0
  answer.value = null
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
    // 数字键 1-4 / 字母 a-d 选释义（与按钮上的 A–D 对应）。
    // 只在「拼完且还没选对」的窗口里接管键盘 —— 拼写期间动键会跟词里的字母打架
    // （比如 abandon 打到 a 时，绝不能把 a 当成选项 A）。
    if (quiz.value && spelled.value && !answer.value) {
      const key = e.key.toLowerCase()
      const i = ['1', '2', '3', '4'].indexOf(key)
      const letter = ['a', 'b', 'c', 'd'].indexOf(key)
      const at = i >= 0 ? i : letter
      if (at >= 0 && props.options[at]) {
        e.preventDefault()
        pick(props.options[at])
        return
      }
    }
    if (e.key.length !== 1) return
    e.preventDefault()
    if (typedCount.value >= chars.value.length) return
    if (e.key === target.value[typedCount.value]) {
      typedCount.value += 1
      trySubmit()
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

    <!-- 跟打：释义改四选一，答对才算过；听写/默写：释义是解题线索，照旧直显 -->
    <div v-if="quiz" class="quiz">
      <p class="quiz-hint">{{ quizHint }}</p>
      <div class="options" :class="{ locked: answer !== null }">
        <button
          v-for="(opt, i) in options"
          :key="opt.word.id"
          class="option-btn"
          :class="{ wrong: isWrongPick(opt.word.id), right: isCorrectPick(opt) }"
          type="button"
          @click="pick(opt)"
        >
          <span class="opt-key">{{ 'ABCD'[i] ?? i + 1 }}</span>
          {{ meaningOf(opt.word) }}
        </button>
      </div>
    </div>
    <p v-else class="meaning">{{ item.translations.map((t) => `${t.pos} ${t.cn}`).join('；') }}</p>

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
        @click="reset"
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

/* 释义四选一：与自测同款的 hairline 选项网格，只是挂在打字板下方 */
.quiz {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.quiz-hint {
  margin: 0;
  color: var(--text-3);
  font-size: 0.82rem;
  text-align: center;
}
.options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 640px;
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
.option-btn.right {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.07);
  pointer-events: none;
}
/* 已作答：整组锁住，鼠标不再有"还能点"的暗示 */
.options.locked .option-btn {
  cursor: default;
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

.board-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}

/* 窄屏：选项一列到底 */
@media (max-width: 680px) {
  .options {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
