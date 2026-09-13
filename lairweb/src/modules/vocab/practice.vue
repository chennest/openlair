<script setup lang="ts">
// 练习页（第二路由入口 /vocab/practice/:bookId?mode=）：
// 开课排课 → 逐词作答（打字/自测）→ 答词复习面板 → 结束页汇总
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { X } from '@lucide/vue'
import {
  vocabApi,
  VOCAB_MODES,
  type QueueItem,
  type VocabMode,
  type VocabSessionSummary,
  type VocabSource,
  type VocabWord,
} from './api'
import { pickDistractors } from './similar'
import PracticeBoard from './PracticeBoard.vue'
import QuestionCard from './QuestionCard.vue'
import WordReveal from './WordReveal.vue'
import PracticeResult from './PracticeResult.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const mode = ref<VocabMode>('follow')
const source = ref<VocabSource>('book')
const bookName = ref('')
const sessionId = ref(0)
const queue = ref<QueueItem[]>([])
const idx = ref(0)
const pool = ref<VocabWord[]>([])

const results = ref<Array<{ word: string; due: string | null; correct: boolean }>>([])
const summary = ref<VocabSessionSummary | null>(null)
const reveal = ref<{ item: QueueItem; correct: boolean; due: string | null } | null>(null)

const startedAt = ref(Date.now())
const elapsedSec = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

const current = computed(() => queue.value[idx.value] ?? null)
const questionOptions = computed(() =>
  current.value && mode.value === 'self_test' ? pickDistractors(current.value, pool.value) : [],
)
const modeLabel = computed(() => VOCAB_MODES.find((m) => m.value === mode.value)?.label ?? '')
const passedCount = computed(() => results.value.filter((r) => r.correct).length)

async function startPractice() {
  loading.value = true
  error.value = ''
  summary.value = null
  reveal.value = null
  results.value = []
  idx.value = 0
  const bookId = Number(route.params.bookId) || 0
  const queryMode = String(route.query.mode ?? 'follow') as VocabMode
  mode.value = VOCAB_MODES.some((m) => m.value === queryMode) ? queryMode : 'follow'
  const querySource = String(route.query.source ?? 'book') as VocabSource
  source.value = ['book', 'wrong', 'collect'].includes(querySource) ? querySource : 'book'
  try {
    const res = await vocabApi.start({ bookId, mode: mode.value, source: source.value })
    sessionId.value = res.id
    queue.value = res.queue
    bookName.value = res.bookName
    // 自测模式的干扰项候选池：词书练习取全词书，错词本/收藏练习取当前队列
    if (mode.value === 'self_test') {
      pool.value =
        source.value === 'book'
          ? (await vocabApi.bookWords(bookId, 100)).words
          : res.queue.map(({ progress: _p, ...w }) => w)
    }
    startedAt.value = Date.now()
    elapsedSec.value = 0
    if (!timer) timer = setInterval(() => (elapsedSec.value = Math.floor((Date.now() - startedAt.value) / 1000)), 1000)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '开课失败'
  } finally {
    loading.value = false
  }
}

async function onDone(payload: { correct: boolean; wrongTimes: number; durationMs: number }) {
  // 复习面板打开期间忽略后续作答事件（如面板下残留的 Esc）
  if (reveal.value || summary.value) return
  const item = current.value
  if (!item) return
  try {
    const res = await vocabApi.answer(sessionId.value, { wordId: item.id, ...payload })
    reveal.value = { item, correct: payload.correct && payload.wrongTimes === 0, due: res.item.due }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '提交失败'
  }
}

async function onContinue() {
  const r = reveal.value
  if (!r) return
  results.value.push({ word: r.item.word, due: r.due, correct: r.correct })
  reveal.value = null
  idx.value += 1
  if (idx.value >= queue.value.length) await finish()
}

async function finish() {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
  try {
    summary.value = (await vocabApi.finish(sessionId.value, elapsedSec.value)).item
  } catch (e) {
    error.value = e instanceof Error ? e.message : '会话汇总失败'
  }
}

function quit() {
  // 未答完中途退出也把会话收尾，保证统计完整
  if (sessionId.value && !summary.value) void vocabApi.finish(sessionId.value, elapsedSec.value).catch(() => {})
  if (timer) clearInterval(timer)
  void router.push('/vocab')
}

onMounted(startPractice)
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在排课…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p><button class="back-link" type="button" @click="router.push('/vocab')">返回词书</button></div></div>

  <div v-else class="practice-page">
    <!-- 顶栏：进度 + 用时 + 退出 -->
    <div v-if="!summary" class="practice-head">
      <button class="quit-btn" type="button" aria-label="退出练习" @click="quit">
        <X class="size-4" />
      </button>
      <div class="head-main">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${(idx / queue.length) * 100}%` }" />
        </div>
        <div class="head-meta">
          <span>《{{ bookName }}》· {{ modeLabel }}练习</span>
          <span class="meta-nums">
            <b>{{ idx }}</b> / {{ queue.length }} ·
            <i class="ok-num">{{ passedCount }}</i> 对 ·
            <i class="no-num">{{ results.length - passedCount }}</i> 错 · {{ elapsedSec }}s
          </span>
        </div>
      </div>
    </div>

    <!-- 结束页 -->
    <PracticeResult
      v-if="summary"
      :summary="summary"
      :words="results"
      @restart="startPractice"
      @back="router.push('/vocab')"
    />

    <!-- 作答区：:key 按词重建，保证每词的打字/选择状态从零开始 -->
    <template v-else-if="current">
      <PracticeBoard
        v-if="mode !== 'self_test'"
        :key="current.id"
        :item="current"
        :mode="mode"
        @done="onDone"
      />
      <QuestionCard
        v-else
        :key="current.id"
        :item="current"
        :options="questionOptions"
        @done="onDone"
      />
    </template>

    <!-- 答词复习面板 -->
    <WordReveal
      v-if="reveal"
      :key="reveal.item.id"
      :item="reveal.item"
      :correct="reveal.correct"
      :due="reveal.due"
      @continue="onContinue"
    />
  </div>
</template>

<style scoped>
.practice-page {
  max-width: 860px;
  margin: 0 auto;
}

.practice-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}
.quit-btn {
  flex: none;
  display: inline-flex;
  padding: 9px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  box-shadow: var(--sh-card);
}
.quit-btn:hover {
  color: #ff3b30;
}
.head-main {
  flex: 1;
  min-width: 0;
}
.progress-track {
  height: 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: width 0.3s var(--ease-out-quart);
}
.head-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 7px;
  font-size: 0.8rem;
  color: var(--text-3);
}
.meta-nums {
  font-variant-numeric: tabular-nums;
}
.meta-nums b {
  color: var(--text-2);
}
.ok-num {
  font-style: normal;
  color: var(--live);
}
.no-num {
  font-style: normal;
  color: var(--heat);
}

.back-link {
  margin-top: 14px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  padding: 8px 18px;
  font-size: 0.85rem;
  color: var(--text-2);
  cursor: pointer;
}
</style>
