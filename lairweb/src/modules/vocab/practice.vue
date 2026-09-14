<script setup lang="ts">
// 练习页（第二路由入口 /vocab/practice/:bookId?mode=&source=&extra=）：
// 开课排课 → 逐词作答（打字/自测）→ 答词复习面板 → 结束页汇总
//
// extra=1 表示「今日任务已达标，再来一组」：本轮显式带 newLimit 越过每日目标。
// 达标之后不留死胡同 —— 无论入口还是结束页，都给出「继续学习」而不是只甩一句完成提示。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  vocabApi,
  VOCAB_MODES,
  type QueueItem,
  type VocabDailyGoal,
  type VocabMode,
  type VocabProgress,
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
/** 完成态：'' 正常排课 / 'goal' 今日目标已达标（可加码继续）/ 'empty' 这个词书真没词可练了 */
const blocked = ref<'' | 'goal' | 'empty'>('')
const blockedMsg = ref('')
const goal = ref<VocabDailyGoal | null>(null)
const extra = ref(false)
const mode = ref<VocabMode>('follow')
const source = ref<VocabSource>('book')
const bookName = ref('')
const sessionId = ref(0)
const queue = ref<QueueItem[]>([])
const idx = ref(0)
const pool = ref<VocabWord[]>([])

const results = ref<Array<{ word: string; due: string | null; correct: boolean }>>([])
const summary = ref<VocabSessionSummary | null>(null)
const reveal = ref<{ item: QueueItem; correct: boolean; due: string | null; progress: VocabProgress | null } | null>(
  null,
)

const startedAt = ref(Date.now())
const elapsedSec = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

const current = computed(() => queue.value[idx.value] ?? null)
const questionOptions = computed(() =>
  current.value && mode.value === 'self_test' ? pickDistractors(current.value, pool.value) : [],
)
const modeLabel = computed(() => VOCAB_MODES.find((m) => m.value === mode.value)?.label ?? '')
const passedCount = computed(() => results.value.filter((r) => r.correct).length)

/** 加码一组的量 = 今日新词目标数；拿不到就退回 10（与后端 DEFAULT_NEW_LIMIT 同值） */
const groupSize = computed(() => goal.value?.newTarget || 10)

/** 今日任务是否全部达标（新词 + 复习两侧）—— 决定主按钮是「继续学习」还是「再来一轮」 */
const goalDone = computed(() => !!goal.value?.achieved && !!goal.value?.reviewAchieved)

/** 开课：over=true 时显式加码一组（越过每日目标，后端「显式 newLimit 优先」通道） */
async function startPractice(opts: { over?: boolean } = {}) {
  loading.value = true
  error.value = ''
  blocked.value = ''
  blockedMsg.value = ''
  summary.value = null
  reveal.value = null
  results.value = []
  idx.value = 0
  const bookId = Number(route.params.bookId) || 0
  const queryMode = String(route.query.mode ?? 'follow') as VocabMode
  mode.value = VOCAB_MODES.some((m) => m.value === queryMode) ? queryMode : 'follow'
  const querySource = String(route.query.source ?? 'book') as VocabSource
  source.value = ['book', 'wrong', 'collect'].includes(querySource) ? querySource : 'book'
  // 入口带 extra=1 就默认一路加码（用户已经表态「还要学」），重开也不再退回目标封顶
  extra.value = extra.value || route.query.extra === '1'
  const over = opts.over ?? extra.value
  try {
    // 目标只是「加码量 + 完成态文案」的依据，取不到不该拖垮整节课 → 静默降级
    if (!goal.value) goal.value = await vocabApi.dailyGoal().catch(() => null)
    // 已达标又没要求加码：默认配额必然一个词都发不出来，直接进完成态，省一次注定 400 的请求
    if (source.value === 'book' && !over && goalDone.value) {
      blocked.value = 'goal'
      blockedMsg.value = '今日新词与复习目标均已完成'
      return
    }
    const res = await vocabApi.start({
      bookId,
      mode: mode.value,
      source: source.value,
      ...(over ? { newLimit: groupSize.value } : {}),
    })
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
    const msg = e instanceof Error ? e.message : '开课失败'
    // 「已完成」「暂无可练习」不是故障，是「没得练」——转成完成态面板。
    // 这两句文案在 backend/app/services/vocab.py 由 pytest 钉住，改那边要同步这里。
    if (msg.includes('已完成')) {
      blocked.value = 'goal'
      blockedMsg.value = msg
    } else if (msg.includes('暂无可练习')) {
      blocked.value = 'empty'
      blockedMsg.value = msg
    } else {
      error.value = msg
    }
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
    reveal.value = {
      item,
      correct: payload.correct && payload.wrongTimes === 0,
      due: res.item.due,
      progress: res.item,
    }
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
    return
  }
  // 刷新目标：结束页要靠它决定主按钮是「继续学习」（已达标）还是「再来一轮」。
  // 取不到不报错 —— 汇总页照常显示，只是退回「再来一轮」。
  goal.value = await vocabApi.dailyGoal().catch(() => goal.value)
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
  <div v-else-if="error" class="placeholder">
    <div>
      <p class="symbol">!</p>
      <p>{{ error }}</p>
      <Button variant="outline" size="sm" class="mt-3.5 rounded-full px-4" @click="router.push('/vocab')">返回词书</Button>
    </div>
  </div>

  <!-- 完成态：达标了就给「继续学习（再来一组）」，而不是只留一句完成提示 -->
  <div v-else-if="blocked" class="practice-page">
    <div class="done-card">
      <p class="done-title">{{ blocked === 'goal' ? '今日任务已完成' : '暂时没有可练的词' }}</p>
      <!-- 直接用后端原话：它已经区分了「两侧都达标」与「新词达标但没到期复习」，
           这里另写一句「都达标了」会在后一种情况下说假话 -->
      <p class="done-sub">{{ blockedMsg }}</p>
      <p v-if="blocked === 'goal'" class="done-sub">
        每组 {{ groupSize }} 个词 · 想学多少都行
      </p>
      <div class="done-actions">
        <Button
          v-if="blocked === 'goal'"
          class="rounded-full px-6 shadow-[var(--sh-cta)]"
          @click="startPractice({ over: true })"
        >继续学习（再来一组）</Button>
        <Button variant="outline" class="rounded-full px-6" @click="router.push('/vocab')">返回词书</Button>
      </div>
    </div>
  </div>

  <div v-else class="practice-page">
    <!-- 顶栏：进度 + 用时 + 退出 -->
    <div v-if="!summary" class="practice-head">
      <Button
        variant="outline"
        size="icon"
        class="flex-none rounded-full bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface)] hover:text-[var(--destructive)]"
        aria-label="退出练习"
        @click="quit"
      >
        <X class="size-4" />
      </Button>
      <div class="head-main">
        <Progress :model-value="(idx / queue.length) * 100" class="h-2 bg-[var(--track)]" aria-label="本次练习进度" />
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
      :goal-done="goalDone"
      @restart="startPractice()"
      @continue="startPractice({ over: true })"
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
      :progress="reveal.progress"
      @continue="onContinue"
    />
  </div>
</template>

<style scoped>
.practice-page {
  max-width: 860px;
  margin: 0 auto;
}

/* 完成态：达标 / 没词可练时替代作答区，主按钮永远是「还有个去处」而不是死胡同 */
.done-card {
  width: min(520px, 100%);
  margin: 24px auto 0;
  padding: 36px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}
.done-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 700;
}
.done-sub {
  margin: 0;
  color: var(--text-3);
  font-size: 0.86rem;
  line-height: 1.6;
}
.done-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}

.practice-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}
.head-main {
  flex: 1;
  min-width: 0;
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
</style>
