<script setup lang="ts">
// 词汇练习主页：学习统计条 + 词书墙 / 错词本 / 收藏 三个 Tab
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  vocabApi,
  type QueueItem,
  type VocabBook,
  type VocabMode,
  type VocabStats,
} from './api'
import BookCard from './BookCard.vue'
import VocabWordRow from './VocabWordRow.vue'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const books = ref<VocabBook[]>([])
const stats = ref<VocabStats | null>(null)
const wrongWords = ref<QueueItem[]>([])
const collectedWords = ref<QueueItem[]>([])

type Filter = 'books' | 'wrong' | 'collect'
const filter = ref<Filter>('books')

const accuracy = computed(() => {
  const t = stats.value?.today
  return t && t.words > 0 ? Math.round((t.correct / t.words) * 100) : null
})

async function load() {
  loading.value = true
  try {
    const [booksRes, statsRes] = await Promise.all([vocabApi.books(), vocabApi.stats()])
    books.value = booksRes.books
    stats.value = statsRes
    wrongWords.value = (await vocabApi.wrong()).words
    collectedWords.value = (await vocabApi.collect()).words
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function onPractice(mode: VocabMode, bookId: number) {
  void router.push(`/vocab/practice/${bookId}?mode=${mode}`)
}

function practiceSource(source: 'wrong' | 'collect') {
  void router.push(`/vocab/practice/0?mode=follow&source=${source}`)
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
      <div v-if="stats" class="stat-strip">
        <div class="stat-item">
          <span class="num">{{ stats.today.words }}</span>
          <span class="label">今日练词</span>
        </div>
        <div class="stat-item">
          <span class="num">{{ accuracy === null ? '—' : `${accuracy}%` }}</span>
          <span class="label">今日正确率</span>
        </div>
        <div class="stat-item">
          <span class="num due">{{ stats.total.due }}</span>
          <span class="label">待复习</span>
        </div>
        <div class="stat-item">
          <span class="num">{{ stats.total.mastered }}</span>
          <span class="label">已掌握</span>
        </div>
      </div>
    </div>

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
      <button
        v-if="filter === 'wrong' && wrongWords.length"
        class="extra-btn"
        type="button"
        @click="practiceSource('wrong')"
      >开始错词练习（{{ wrongWords.length }}）</button>
      <button
        v-if="filter === 'collect' && collectedWords.length"
        class="extra-btn"
        type="button"
        @click="practiceSource('collect')"
      >复习收藏（{{ collectedWords.length }}）</button>
    </div>

    <!-- 词书墙 -->
    <div v-if="filter === 'books'" class="card-wall">
      <BookCard v-for="b in books" :key="b.id" :book="b" @practice="(m) => onPractice(m, b.id)" />
      <div v-if="!books.length" class="placeholder empty"><div><p>还没有词书，用后端导入脚本添加</p></div></div>
    </div>

    <!-- 错词本 -->
    <div v-else-if="filter === 'wrong'" class="word-list">
      <VocabWordRow
        v-for="w in wrongWords"
        :key="w.id"
        :item="w"
        source="wrong"
        @dismiss-wrong="onDismissWrong"
        @master="onMaster"
      />
      <div v-if="!wrongWords.length" class="placeholder empty"><div><p>错词本是空的，继续保持！</p></div></div>
    </div>

    <!-- 收藏 -->
    <div v-else class="word-list">
      <VocabWordRow
        v-for="w in collectedWords"
        :key="w.id"
        :item="w"
        source="collect"
        @uncollect="onUncollect"
      />
      <div v-if="!collectedWords.length" class="placeholder empty"><div><p>还没有收藏的单词</p></div></div>
    </div>
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

.stat-strip {
  display: flex;
  gap: 22px;
  padding: 12px 20px;
  background: var(--surface);
  border-radius: var(--r-card);
  box-shadow: var(--sh-card);
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.num {
  font-size: 1.2rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.num.due {
  color: var(--heat);
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
  margin: 22px 0 4px;
}
.extra-btn {
  padding: 8px 18px;
  border: none;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--sh-cta);
}
.extra-btn:hover {
  filter: brightness(1.05);
}
.extra-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.word-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  .stat-strip {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
