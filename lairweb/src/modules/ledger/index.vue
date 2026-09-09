<script setup lang="ts">
// 记账模块页：账本切换 + 横幅摘要 + slim 摘要条 + 流水通栏（筛选内嵌）+ 弹窗，负责数据加载与查询状态
import { computed, onMounted, ref } from 'vue'
import { Check, Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import {
  ledgerApi,
  bookApi,
  type Book,
  type Category,
  type LedgerData,
  type LedgerQuery,
  type Transaction,
} from './api'
import BookSwitcher from './BookSwitcher.vue'
import BookManage from './BookManage.vue'
import BookCreate from './BookCreate.vue'
import BookJoin from './BookJoin.vue'
import BookTrash from './BookTrash.vue'
import LedgerSummary from './LedgerSummary.vue'
import LedgerStrip from './LedgerStrip.vue'
import LedgerFilter from './LedgerFilter.vue'
import LedgerTable from './LedgerTable.vue'
import LedgerDialog from './LedgerDialog.vue'

const loading = ref(true)
const error = ref('')
const data = ref<LedgerData | null>(null)
const trend = ref<Awaited<ReturnType<typeof ledgerApi.trend>>>([])
const categories = ref<Category[]>([])

// 账本状态
const books = ref<Book[]>([])
const currentBookId = ref(0)
const currentBook = computed(() => books.value.find((b) => b.id === currentBookId.value) ?? null)
const showManage = ref(false)
const showCreate = ref(false)
const showJoin = ref(false)
const joinSubmitting = ref(false)
const joinError = ref('')
const inviteCode = ref<string | null>(null)

/** 无账本空态 */
const noBooks = computed(() => books.value.length === 0)
const showTrash = ref(false)
const trashBooks = ref<Book[]>([])

const showDialog = ref(false)
/** 正在编辑的流水（null = 记一笔模式） */
const editingTx = ref<Transaction | null>(null)
const savedTip = ref(false)

// 查询状态（筛选栏 + 分页；bookId 跟随当前账本）
const query = ref<LedgerQuery>({ page: 1, pageSize: 20 })

async function loadBooks() {
  try {
    books.value = await bookApi.list()
    // 当前账本失效（被删/不存在）时切到第一个账本
    if (!books.value.some((b) => b.id === currentBookId.value)) {
      currentBookId.value = books.value[0]?.id ?? 0
    }
  } catch {
    books.value = []
    currentBookId.value = 0
  }
}

async function load() {
  if (!currentBookId.value) {
    data.value = null
    loading.value = false
    return
  }
  // 初次加载才全屏 loading;切换筛选/账本时静默刷新(保留页面内容,避免闪烁)
  const isInitial = !data.value
  if (isInitial) loading.value = true
  try {
    const q: LedgerQuery = { ...query.value, bookId: currentBookId.value }
    const [d, t] = await Promise.all([ledgerApi.list(q), ledgerApi.trend(currentBookId.value)])
    data.value = d
    trend.value = t
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function switchBook(bookId: number) {
  currentBookId.value = bookId
  query.value = { page: 1, pageSize: 20 }
  await load()
}

async function handleQueryChange(q: LedgerQuery) {
  query.value = { ...query.value, ...q }
  await load()
}

async function handleCreate(payload: Parameters<typeof ledgerApi.create>[0]) {
  try {
    // 记账人由后端从 token 解析（mock 与真实后端一致）
    await ledgerApi.create({ ...payload, bookId: currentBookId.value })
    showDialog.value = false
    savedTip.value = true
    setTimeout(() => (savedTip.value = false), 2000)
    await load()
  } finally {
    // 弹窗内 saving 状态由父组件提交完成后复位
  }
}

/** 打开编辑弹窗：预填该条流水 */
function openEdit(tx: Transaction) {
  editingTx.value = tx
  showDialog.value = true
}

/** 关闭弹窗：同时清掉编辑态，避免再次打开停在编辑模式 */
function closeDialog() {
  showDialog.value = false
  editingTx.value = null
}

async function handleUpdate(payload: { id: number; patch: Parameters<typeof ledgerApi.update>[1] }) {
  await ledgerApi.update(payload.id, payload.patch)
  closeDialog()
  savedTip.value = true
  setTimeout(() => (savedTip.value = false), 2000)
  await load()
}

async function handleRemove(id: number) {
  await ledgerApi.remove(id)
  await load()
}

async function handleBudgetSave(amount: number) {
  await ledgerApi.updateBudget(currentBookId.value, amount)
  await load()
}

// 账本操作
async function handleBookCreate(input: { name: string; type: 'personal' | 'shared' }) {
  const r = await bookApi.create(input)
  showCreate.value = false
  await loadBooks()
  if (r.book) {
    currentBookId.value = r.book.id
    await load()
  }
}

async function handleMemberRemove(userId: number) {
  const r = await bookApi.removeMember(currentBookId.value, userId)
  if (r.book) await loadBooks()
}

async function handleBookConvert() {
  if (!currentBookId.value) return
  const r = await bookApi.convertToShared(currentBookId.value)
  if (r.book) {
    showManage.value = false
    await loadBooks()
  }
}

// 邀请码 / 加入 / 退出

async function openManage() {
  inviteCode.value = null
  if (currentBookId.value) {
    try {
      inviteCode.value = (await bookApi.getInvite(currentBookId.value)).code
    } catch {
      inviteCode.value = null
    }
  }
  showManage.value = true
}

async function handleResetInvite() {
  if (!currentBookId.value) return
  try {
    inviteCode.value = (await bookApi.resetInvite(currentBookId.value)).code
  } catch {
    /* 错误已在信封层统一抛出提示 */
  }
}

async function handleDisableInvite() {
  if (!currentBookId.value) return
  await bookApi.disableInvite(currentBookId.value)
  inviteCode.value = null
}

async function handleLeave() {
  if (!currentBookId.value) return
  await bookApi.leave(currentBookId.value)
  showManage.value = false
  await loadBooks()
  const active = books.value.filter((b) => !b.deletedAt)
  if (!active.find((b) => b.id === currentBookId.value)) {
    currentBookId.value = active[0]?.id ?? 0
  }
  await load()
}

async function handleJoin(code: string) {
  joinSubmitting.value = true
  joinError.value = ''
  try {
    const r = await bookApi.joinByCode(code)
    showJoin.value = false
    await loadBooks()
    currentBookId.value = r.book.id
    await load()
  } catch (e) {
    joinError.value = e instanceof Error ? e.message : '加入失败'
  } finally {
    joinSubmitting.value = false
  }
}

// 软删除账本
async function handleBookDelete() {
  await bookApi.softDelete(currentBookId.value)
  showManage.value = false
  await loadBooks()
  // 如果当前账本被删，切换到剩余第一个账本
  const active = books.value.filter((b) => !b.deletedAt)
  if (active.length === 0) return
  if (!active.find((b) => b.id === currentBookId.value)) {
    currentBookId.value = active[0].id
    await load()
  }
}

// 回收站
async function loadTrash() {
  try {
    trashBooks.value = await bookApi.trash()
  } catch {
    trashBooks.value = []
  }
}

async function handleRestore(bookId: number) {
  await bookApi.restore(bookId)
  await loadTrash()
  await loadBooks()
}

async function handlePurge(bookId: number) {
  await bookApi.purge(bookId)
  await loadTrash()
  await loadBooks()
}

async function openTrash() {
  await loadTrash()
  showTrash.value = true
}

onMounted(async () => {
  try {
    categories.value = await ledgerApi.categories()
  } catch {
    categories.value = []
  }
  await loadBooks()
  await load()
})
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载账本…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>
  <div v-else-if="noBooks" class="empty-state">
    <p class="empty-symbol">📒</p>
    <p class="empty-title">还没有账本</p>
    <p class="empty-desc">创建一个账本开始记账，或输入邀请码加入家人朋友的共享账本</p>
    <div class="empty-actions">
      <Button @click="showCreate = true">
        <Plus class="size-4" />
        新建账本
      </Button>
      <Button variant="outline" @click="showJoin = true">
        <Plus class="size-4" />
        加入共享账本
      </Button>
    </div>
  </div>

  <div v-else class="ledger">
    <div class="book-bar">
      <BookSwitcher
        :books="books"
        :current="currentBook"
        @switch="switchBook"
        @create="showCreate = true"
        @manage="openManage"
        @join="showJoin = true"
        @trash="openTrash"
      />
    </div>

    <LedgerSummary :summary="data!.summary">
      <template #action>
        <div class="hero-actions">
          <Button
            variant="ghost"
            class="h-10 pl-5 pr-5 rounded-full! bg-[rgba(255,255,255,0.16)] border border-white/22 backdrop-blur-[8px] text-white font-semibold text-[0.92rem] cursor-pointer transition-all duration-[160ms] ease-[var(--ease-out-quart)] hover:bg-white/26 hover:text-white disabled:opacity-[0.45] disabled:cursor-not-allowed"
            :disabled="books.length === 0"
            :title="books.length === 0 ? '请先创建账本' : ''"
            @click="showDialog = true"
          >
            <Plus class="size-4" />
            记一笔
          </Button>
          <Transition name="fade">
            <span v-if="savedTip" class="saved-tip">
              <Check class="size-3.5" />
              已记录
            </span>
          </Transition>
        </div>
      </template>
    </LedgerSummary>

    <!-- 摘要条：统计压缩为一行，只占一点高度 -->
    <LedgerStrip
      :summary="data!.summary"
      :budget="data!.budget"
      :trend="trend"
      @save-budget="handleBudgetSave"
    />

    <!-- 流水主体：筛选收进卡片头部，列表通栏按日分组 -->
    <LedgerTable
      :transactions="data!.transactions"
      :total="data!.total"
      :page="data!.page"
      :page-size="data!.pageSize"
      :shared="currentBook?.type === 'shared'"
      @remove="handleRemove"
      @edit="openEdit"
      @page="(p: number) => handleQueryChange({ page: p })"
      @page-size="(s: number) => handleQueryChange({ pageSize: s, page: 1 })"
    >
      <template #toolbar>
        <LedgerFilter :categories="categories" :value="query" @change="handleQueryChange" />
      </template>
    </LedgerTable>

    <LedgerDialog
      :open="showDialog"
      :categories="categories"
      :transaction="editingTx"
      @close="closeDialog"
      @submit="handleCreate"
      @update="handleUpdate"
    />

    <BookManage
      :open="showManage"
      :book="currentBook"
      :invite-code="inviteCode"
      @close="showManage = false"
      @remove="handleMemberRemove"
      @delete="handleBookDelete"
      @convert="handleBookConvert"
      @reset-invite="handleResetInvite"
      @disable-invite="handleDisableInvite"
      @leave="handleLeave"
    />

    <BookTrash
      :open="showTrash"
      :books="trashBooks"
      @close="showTrash = false"
      @restore="handleRestore"
      @purge="handlePurge"
    />
  </div>

  <!-- 新建账本弹窗（空态/正常态共用） -->
  <BookCreate :open="showCreate" @close="showCreate = false" @create="handleBookCreate" />

  <!-- 加入共享账本弹窗（空态/正常态共用，新用户无账本时也能加入） -->
  <BookJoin
    :open="showJoin"
    :submitting="joinSubmitting"
    :error="joinError"
    @close="showJoin = false"
    @join="handleJoin"
  />
</template>

<style scoped>
.ledger {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.book-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.saved-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 600;
  font-size: 0.88rem;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 240ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.placeholder {
  display: grid;
  place-items: center;
  min-height: 46vh;
  text-align: center;
  border: 1px dashed var(--faint);
  border-radius: var(--r-panel);
  background: var(--surface);
  color: var(--text-3);
}
.placeholder .symbol {
  font-size: 2.4rem;
  margin-bottom: 12px;
  color: var(--accent);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 72px 24px;
  border: 1px dashed var(--faint);
  border-radius: var(--r-panel);
  background: var(--surface);
  text-align: center;
}
.empty-symbol {
  font-size: 2.6rem;
  margin: 0 0 4px;
}
.empty-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
}
.empty-desc {
  margin: 0 0 14px;
  font-size: 0.9rem;
  color: var(--text-3);
}
.empty-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
.empty-actions :deep(button) {
  height: 44px;
  padding: 0 22px;
  border-radius: var(--r-pill);
  font-size: 0.92rem;
  font-weight: 600;
}
</style>
