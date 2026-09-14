<script setup lang="ts">
// 词汇练习主页：学习统计条 + 词书墙 / 错词本 / 收藏 三个 Tab
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getUser } from '@/api/request'
import { Plus } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  vocabApi,
  type ImportBooksResult,
  type QueueItem,
  type VocabBook,
  type VocabDailyGoal,
  type VocabImportScope,
  type VocabMode,
  type VocabStats,
} from './api'
import BookCard from './BookCard.vue'
import DailyGoalCard from './DailyGoalCard.vue'
import VocabWordRow from './VocabWordRow.vue'
import VocabImportDialog from './VocabImportDialog.vue'
import StatStrip, { type StatItem } from './StatStrip.vue'

const router = useRouter()
const currentUserId = Number((getUser() as { id?: number } | null)?.id ?? 0)

const loading = ref(true)
const error = ref('')
const books = ref<VocabBook[]>([])
const stats = ref<VocabStats | null>(null)
const goal = ref<VocabDailyGoal | null>(null)
const goalSaving = ref(false)
const goalError = ref('')
const wrongWords = ref<QueueItem[]>([])
const collectedWords = ref<QueueItem[]>([])

type Filter = 'books' | 'wrong' | 'collect'
const filter = ref<Filter>('books')

// ---------- 导入词书弹窗 ----------
const importOpen = ref(false)
const importing = ref(false)
const importResult = ref<ImportBooksResult | null>(null)
const importError = ref('')

const accuracy = computed(() => {
  const t = stats.value?.today
  return t && t.words > 0 ? Math.round((t.correct / t.words) * 100) : null
})

/** 今日概览：只有「待复习」用 heat 强调，其余走灰阶 */
const statItems = computed<StatItem[]>(() => [
  { num: stats.value?.today.words ?? 0, label: '今日练词' },
  { num: accuracy.value === null ? '—' : `${accuracy.value}%`, label: '今日正确率' },
  { num: stats.value?.total.due ?? 0, label: '待复习', tone: 'heat' },
  { num: stats.value?.total.mastered ?? 0, label: '已记住' },
])

/** 当前 Tab 的列表数据（错词本 / 收藏共用一套行组件） */
const currentList = computed(() => (filter.value === 'wrong' ? wrongWords.value : collectedWords.value))
const listTitle = computed(() => (filter.value === 'wrong' ? '错词本' : '收藏'))

async function load() {
  loading.value = true
  try {
    const [booksRes, statsRes, goalRes] = await Promise.all([
      vocabApi.books(),
      vocabApi.stats(),
      vocabApi.dailyGoal(),
    ])
    books.value = booksRes.books
    stats.value = statsRes
    goal.value = goalRes
    wrongWords.value = (await vocabApi.wrong()).words
    collectedWords.value = (await vocabApi.collect()).words
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

/** 改每日目标：只提交变化的字段，成功后用后端回读的完整视图覆盖（含今日进度），弹窗据此自动收起 */
async function onSaveGoal(patch: { newTarget?: number; reviewTarget?: number }) {
  goalSaving.value = true
  goalError.value = ''
  try {
    goal.value = await vocabApi.setDailyGoal(patch)
  } catch (e) {
    goalError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    goalSaving.value = false
  }
}

function onPractice(mode: VocabMode, bookId: number) {
  void router.push(`/vocab/practice/${bookId}?mode=${mode}`)
}

/** 今日任务入口的目标词书：优先挑有待复习的词书（最该练的那本），否则第一本 */
const todayBook = computed(() => books.value.find((b) => b.due > 0) ?? books.value[0] ?? null)

/**
 * 入口该不该加码 —— 与 DailyGoalCard 的 fullyDone 同一判据，两边必须一致，
 * 否则会出现「按钮写着开始学习、点了却直接掉进完成态」。
 */
const todayOver = computed(() => {
  const g = goal.value
  if (!g?.achieved) return false
  return g.reviewAchieved || (todayBook.value?.due ?? 0) === 0
})

/**
 * 今日任务入口：未达标就按「每日目标剩余量」开课（后端默认行为）；该加码时显式加一组
 * （extra=1，练习页把 newLimit 设成今日新词目标数）。后端 start_session 里
 * 「显式 newLimit 优先于目标剩余量」这条通道本就是留给「今天想多学一轮」的，这里只是把它接出来。
 */
function startToday() {
  const book = todayBook.value
  if (!book) {
    openImport()
    return
  }
  void router.push(`/vocab/practice/${book.id}?mode=follow${todayOver.value ? '&extra=1' : ''}`)
}

function onOpenBook(bookId: number) {
  void router.push(`/vocab/book/${bookId}`)
}

function practiceSource(source: 'wrong' | 'collect') {
  void router.push(`/vocab/practice/0?mode=follow&source=${source}`)
}

async function onImport(input: { name: string; scope: VocabImportScope; lang: string; text: string }) {
  importing.value = true
  importError.value = ''
  try {
    importResult.value = await vocabApi.importBooks(input)
    await load()
  } catch (e) {
    importError.value = e instanceof Error ? e.message : '导入失败'
  } finally {
    importing.value = false
  }
}

function openImport() {
  importResult.value = null
  importError.value = ''
  importOpen.value = true
}

async function onDeleteBook(bookId: number) {
  try {
    await vocabApi.deleteBook(bookId)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function onDismissWrong(wordId: number) {
  await vocabApi.updateProgress(wordId, { dismissWrong: true })
  wrongWords.value = wrongWords.value.filter((w) => w.id !== wordId)
}

async function onMaster(wordId: number) {
  await vocabApi.updateProgress(wordId, { status: 'mastered', dismissWrong: true })
  wrongWords.value = wrongWords.value.filter((w) => w.id !== wordId)
  await load()
}

async function onUncollect(wordId: number) {
  await vocabApi.updateProgress(wordId, { collected: false })
  collectedWords.value = collectedWords.value.filter((w) => w.id !== wordId)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载词书…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="vocab-page">
    <!-- 页头 + 今日统计 -->
    <div class="page-head">
      <div>
        <h1>词汇练习</h1>
        <p class="page-sub">一次敲击，一点进步 · 打字即背词</p>
      </div>
      <StatStrip v-if="stats" :items="statItems" />
      <Button size="sm" class="rounded-full px-4 shadow-[var(--sh-cta)]" @click="openImport">
        <Plus class="size-4" />
        导入词书
      </Button>
    </div>

    <!-- 每日背词目标：今日已记 / 目标，可就地改目标；卡底是今日任务入口（未完成「开始学习（今日任务）」/ 达标「继续学习（再来一组）」） -->
    <DailyGoalCard
      v-if="goal"
      :goal="goal"
      :saving="goalSaving"
      :error="goalError"
      :can-start="books.length > 0"
      :due-in-book="todayBook?.due ?? 0"
      @save="onSaveGoal"
      @start="startToday"
    />

    <!-- Tab：词书 / 错词本 / 收藏 -->
    <div class="toolbar">
      <Tabs v-model="filter">
        <TabsList class="seg">
          <TabsTrigger
            v-for="f in [
              { value: 'books', label: '词书' },
              { value: 'wrong', label: `错词本${wrongWords.length ? ` ${wrongWords.length}` : ''}` },
              { value: 'collect', label: `收藏${collectedWords.length ? ` ${collectedWords.length}` : ''}` },
            ]"
            :key="f.value"
            :value="f.value"
            class="h-auto px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
          >{{ f.label }}</TabsTrigger>
        </TabsList>
      </Tabs>
      <Button
        v-if="filter === 'wrong' && wrongWords.length"
        variant="outline"
        size="sm"
        class="rounded-full px-4"
        @click="practiceSource('wrong')"
      >开始错词练习（{{ wrongWords.length }}）</Button>
      <Button
        v-if="filter === 'collect' && collectedWords.length"
        variant="outline"
        size="sm"
        class="rounded-full px-4"
        @click="practiceSource('collect')"
      >复习收藏（{{ collectedWords.length }}）</Button>
    </div>

    <!-- 词书墙 -->
    <template v-if="filter === 'books'">
      <div v-if="books.length" class="card-wall">
        <BookCard
          v-for="b in books"
          :key="b.id"
          :book="b"
          :can-delete="b.ownerId === currentUserId || (b.ownerId === null && currentUserId === 1)"
          @practice="(m) => onPractice(m, b.id)"
          @open="onOpenBook"
          @delete="onDeleteBook"
        />
        <!-- 词书不满一行时补一张导入卡：既填掉右侧留白，也是自然的入口 -->
        <button v-if="books.length < 3" type="button" class="import-tile" @click="openImport">
          <Plus class="size-5" />
          <span class="import-title">导入词书</span>
          <span class="import-sub">Anki / ECDICT / 纯文本</span>
        </button>
      </div>
      <div v-else class="placeholder empty"><div><p>还没有词书，点右上角「导入词书」添加</p></div></div>
    </template>

    <!-- 错词本 / 收藏：一个面板 + hairline 行 -->
    <article v-else-if="currentList.length" class="card list-panel">
      <div class="card-title">
        <span>{{ listTitle }}</span>
        <Badge variant="secondary">{{ currentList.length }}</Badge>
      </div>
      <div class="row-list">
        <VocabWordRow
          v-for="w in currentList"
          :key="w.id"
          :item="w"
          :source="filter === 'wrong' ? 'wrong' : 'collect'"
          @dismiss-wrong="onDismissWrong"
          @master="onMaster"
          @uncollect="onUncollect"
        />
      </div>
    </article>

    <div v-else class="placeholder empty">
      <div><p>{{ filter === 'wrong' ? '错词本是空的，继续保持！' : '还没有收藏的单词' }}</p></div>
    </div>

    <!-- 导入词书弹窗 -->
    <VocabImportDialog
      :open="importOpen"
      :importing="importing"
      :result="importResult"
      :error="importError"
      @close="importOpen = false"
      @submit="onImport"
    />
  </div>
</template>

<style scoped>
.vocab-page {
  max-width: var(--max-grid);
  margin: 0 auto;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.page-sub {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 0.9rem;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin: 22px 0 4px;
}
.seg {
  height: auto;
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--r-pill);
  padding: 3px;
  gap: 2px;
}

.card-wall {
  display: grid;
  /* min() 兜底：窄屏（容器 < 320px）时塌成单列铺满，不溢出 */
  grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr));
  align-items: start;
  gap: 18px;
  margin-top: 18px;
}

/* 导入占位卡：虚线框，与词书卡同尺寸，把词书不满一行的留白收口 */
.import-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 182px;
  padding: 20px;
  border: 1px dashed var(--faint);
  border-radius: var(--r-card);
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  transition: border-color 0.25s var(--ease-out-quart), background 0.25s var(--ease-out-quart),
    color 0.25s var(--ease-out-quart);
}
.import-tile:hover {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.04);
  color: var(--accent);
}
.import-tile:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.import-title {
  font-size: 0.92rem;
  font-weight: 600;
}
.import-sub {
  font-size: 0.78rem;
  color: var(--text-4);
}

.list-panel {
  margin-top: 18px;
}

.empty {
  margin-top: 18px;
}

@media (max-width: 860px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }
  .page-head :deep(.stat-strip) {
    width: 100%;
  }
}
</style>
