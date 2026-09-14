<script setup lang="ts">
// 词书详情页：汇总统计 + 状态筛选/搜索/排序 + 单词列表（进度 / 模式覆盖 / 行内操作）
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUser } from '@/api/request'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  vocabApi,
  type BookSummary,
  type BookWordItem,
  type VocabProgress,
  type VocabWordFilter,
  type VocabWordSort,
} from './api'
import BookWordRow from './BookWordRow.vue'

const route = useRoute()
const router = useRouter()
const bookId = Number(route.params.id) || 0
const currentUserId = Number((getUser() as { id?: number } | null)?.id ?? 0)

const PAGE_SIZE = 50

const loading = ref(true)
const error = ref('')
const summary = ref<BookSummary | null>(null)

const words = ref<BookWordItem[]>([])
const total = ref(0)
const listLoading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(false)
const offset = ref(0)

const filter = ref<VocabWordFilter>('all')
const keyword = ref('')
const sort = ref<VocabWordSort>('order')

const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | undefined
let searchTimer: ReturnType<typeof setTimeout> | undefined

const SORTS: Array<{ value: VocabWordSort; label: string }> = [
  { value: 'order', label: '词书顺序' },
  { value: 'freq', label: '词频' },
  { value: 'wrong', label: '错次最多' },
  { value: 'recent', label: '最近练习' },
]

/** 筛选 Tab：计数来自词书汇总（全部 = 词书总词数） */
const FILTERS = computed<Array<{ value: VocabWordFilter; label: string }>>(() => {
  const s = summary.value
  return [
    { value: 'all', label: `全部 ${s?.total ?? 0}` },
    { value: 'unlearned', label: `未学 ${s?.unlearned ?? 0}` },
    { value: 'learning', label: `学习中 ${s?.learning ?? 0}` },
    { value: 'mastered', label: `已掌握 ${s?.mastered ?? 0}` },
    { value: 'wrong', label: `错词 ${s?.wrong ?? 0}` },
    { value: 'collected', label: `收藏 ${s?.collected ?? 0}` },
  ]
})

const canDelete = computed(() => {
  const s = summary.value
  if (!s) return false
  return s.book.ownerId === currentUserId || (s.book.ownerId === null && currentUserId === 1)
})

const query = () => ({ status: filter.value, keyword: keyword.value.trim(), sort: sort.value })

async function loadSummary() {
  summary.value = await vocabApi.bookSummary(bookId)
}

async function loadFirstPage() {
  listLoading.value = true
  try {
    const res = await vocabApi.bookWords(bookId, PAGE_SIZE, 0, query())
    words.value = res.words
    total.value = res.total
    offset.value = res.words.length
    hasMore.value = offset.value < res.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    listLoading.value = false
  }
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || listLoading.value) return
  loadingMore.value = true
  try {
    const res = await vocabApi.bookWords(bookId, PAGE_SIZE, offset.value, query())
    const seen = new Set(words.value.map((w) => w.id))
    words.value = [...words.value, ...res.words.filter((w) => !seen.has(w.id))]
    offset.value += res.words.length
    hasMore.value = offset.value < res.total
  } catch {
    hasMore.value = false
  } finally {
    loadingMore.value = false
  }
}

async function boot() {
  loading.value = true
  error.value = ''
  try {
    await loadSummary()
    await loadFirstPage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

/** 行内操作后就地更新该行，避免整页重载打断滚动位置 */
function applyProgress(wordId: number, p: VocabProgress) {
  const idx = words.value.findIndex((w) => w.id === wordId)
  if (idx < 0) return
  const dropped =
    (filter.value === 'collected' && !p.collected) || (filter.value === 'wrong' && !p.wrongActive)
  if (dropped) {
    words.value.splice(idx, 1)
    total.value = Math.max(0, total.value - 1)
    offset.value = Math.max(0, offset.value - 1)
  } else {
    words.value[idx] = { ...words.value[idx]!, progress: p }
  }
}

async function onCollect(wordId: number) {
  const row = words.value.find((w) => w.id === wordId)
  const next = !(row?.progress?.collected ?? false)
  try {
    const res = await vocabApi.updateProgress(wordId, { collected: next })
    applyProgress(wordId, res.item)
    void loadSummary()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function onMaster(wordId: number) {
  const row = words.value.find((w) => w.id === wordId)
  const next = row?.progress?.status === 'mastered' ? 'learning' : 'mastered'
  try {
    const res = await vocabApi.updateProgress(wordId, { status: next, dismissWrong: next === 'mastered' })
    applyProgress(wordId, res.item)
    void loadSummary()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function onDismissWrong(wordId: number) {
  try {
    const res = await vocabApi.updateProgress(wordId, { dismissWrong: true })
    applyProgress(wordId, res.item)
    void loadSummary()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

function startPractice() {
  void router.push(`/vocab/practice/${bookId}?mode=follow`)
}

async function onDeleteBook() {
  const s = summary.value
  if (!s) return
  if (!window.confirm(`确定删除词书「${s.book.name}」吗？学习进度会保留。`)) return
  try {
    await vocabApi.deleteBook(bookId)
    void router.push('/vocab')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

watch([filter, sort], () => {
  void loadFirstPage()
})

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadFirstPage(), 300)
})

watch([sentinel, loading], () => {
  observer?.disconnect()
  if (!sentinel.value || loading.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) void loadMore()
    },
    { rootMargin: '240px' },
  )
  observer.observe(sentinel.value)
}, { flush: 'post' })

onMounted(boot)
onUnmounted(() => {
  observer?.disconnect()
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载词书…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else-if="summary" class="book-page">
    <div class="page-head">
      <div class="head-left">
        <button class="back-btn" type="button" @click="router.push('/vocab')">返回词书墙</button>
        <h1>
          {{ summary.book.emoji || '📖' }} {{ summary.book.name }}
          <span v-if="summary.book.ownerId !== null" class="mine-badge">我的</span>
        </h1>
        <p class="page-sub">
          {{ summary.total }} 个单词<span v-if="summary.book.description"> · {{ summary.book.description }}</span>
        </p>
      </div>
      <div class="head-actions">
        <Button size="sm" class="rounded-full px-4" @click="startPractice">开始练习</Button>
        <Button v-if="canDelete" size="sm" variant="outline" class="rounded-full px-4" @click="onDeleteBook">
          删除词书
        </Button>
      </div>
    </div>

    <div class="stat-panel">
      <div class="stat"><span class="num">{{ summary.total }}</span><span class="label">总词数</span></div>
      <div class="stat"><span class="num">{{ summary.learned }}</span><span class="label">已学</span></div>
      <div class="stat"><span class="num">{{ summary.mastered }}</span><span class="label">已掌握</span></div>
      <div class="stat"><span class="num due">{{ summary.due }}</span><span class="label">待复习</span></div>
      <div class="stat"><span class="num wrong">{{ summary.wrong }}</span><span class="label">错词</span></div>
      <div class="stat"><span class="num muted">{{ summary.unlearned }}</span><span class="label">未学</span></div>
    </div>

    <div class="toolbar">
      <Tabs v-model="filter">
        <TabsList class="seg">
          <TabsTrigger
            v-for="f in FILTERS"
            :key="f.value"
            :value="f.value"
            class="h-auto px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
          >{{ f.label }}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div class="tools">
        <Input v-model="keyword" class="search" placeholder="搜索单词…" />
        <NativeSelect v-model="sort" size="sm" class="sorter">
          <NativeSelectOption v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</NativeSelectOption>
        </NativeSelect>
      </div>
    </div>

    <div class="panel">
      <BookWordRow
        v-for="w in words"
        :key="w.id"
        :item="w"
        @collect="onCollect"
        @master="onMaster"
        @dismiss-wrong="onDismissWrong"
      />
      <div v-if="!words.length" class="panel-empty">
        {{ listLoading ? '加载中…' : '没有符合条件的单词' }}
      </div>
      <div v-else-if="listLoading" class="panel-loading">加载中…</div>
    </div>

    <div ref="sentinel" class="sentinel">
      <span v-if="loadingMore">正在加载更多…</span>
      <span v-else-if="!hasMore && words.length">已到底部 · 共 {{ total }} 个单词</span>
    </div>
  </div>
</template>

<style scoped>
.book-page {
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
.head-left h1 {
  display: flex;
  align-items: center;
  gap: 10px;
}
.back-btn {
  margin-bottom: 8px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text-3);
  font-size: 0.8rem;
  cursor: pointer;
}
.back-btn:hover {
  color: var(--accent);
}
.back-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.mine-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 600;
}
.page-sub {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 0.86rem;
}
.head-actions {
  display: flex;
  gap: 8px;
}

.stat-panel {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  padding: 14px 8px;
  background: var(--surface);
  border-radius: var(--r-card);
  box-shadow: var(--sh-card);
}
.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat + .stat {
  border-left: 1px solid var(--hairline);
}
.num {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.num.due {
  color: var(--heat);
}
.num.wrong {
  color: #d70015;
}
.num.muted {
  color: var(--text-3);
}
.label {
  font-size: 0.72rem;
  color: var(--text-3);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 20px 0 12px;
  flex-wrap: wrap;
}
.seg {
  height: auto;
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--r-pill);
  padding: 3px;
  gap: 2px;
}
.tools {
  display: flex;
  align-items: center;
  gap: 8px;
}
.search {
  width: 180px;
}
.sorter {
  width: 130px;
}

.panel {
  background: var(--surface);
  border-radius: var(--r-card);
  box-shadow: var(--sh-card);
  overflow: hidden;
}
.panel-empty,
.panel-loading {
  padding: 28px 16px;
  text-align: center;
  color: var(--text-3);
  font-size: 0.86rem;
}
.sentinel {
  padding: 18px 0 6px;
  text-align: center;
  color: var(--text-4);
  font-size: 0.78rem;
  min-height: 24px;
}

@media (max-width: 680px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }
  .stat-panel {
    flex-wrap: wrap;
    gap: 12px 0;
  }
  .stat {
    flex: 0 0 33.33%;
  }
  .stat + .stat {
    border-left: none;
  }
  .tools {
    width: 100%;
  }
  .search {
    flex: 1;
    width: auto;
  }
}
</style>
