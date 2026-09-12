<script setup lang="ts">
// 倒数日模块页：卡片墙大数字 + 全部/倒数/纪念日筛选 + 新建/编辑弹窗
import { computed, onMounted, ref } from 'vue'
import { Plus } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { daysApi, type CreateDayInput, type DayItem } from './api'
import DayCard from './DayCard.vue'
import DayDialog from './DayDialog.vue'

const loading = ref(true)
const error = ref('')
const days = ref<DayItem[]>([])

type Filter = 'all' | 'future' | 'memorial'
const filter = ref<Filter>('all')

// ---------- 弹窗状态 ----------
const formOpen = ref(false)
const editing = ref<DayItem | null>(null)
const saving = ref(false)
const busy = ref(false)

/** 筛选语义：倒数 = 一次性未到（含今天）；纪念日 = 每年/每月重复，或一次性已过（累计天数） */
const filtered = computed(() =>
  days.value.filter((d) => {
    if (filter.value === 'all') return true
    if (filter.value === 'future') return d.repeat === 'once' && d.daysUntil >= 0
    return d.repeat !== 'once' || d.daysUntil < 0
  }),
)

/** 最近一个未到的日子（摘要用） */
const nearest = computed(() =>
  days.value.filter((d) => d.daysUntil > 0).sort((a, b) => a.daysUntil - b.daysUntil)[0] ?? null,
)

async function load() {
  loading.value = true
  try {
    days.value = (await daysApi.list()).days
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  formOpen.value = true
}

function openEdit(id: number) {
  editing.value = days.value.find((d) => d.id === id) ?? null
  if (editing.value) formOpen.value = true
}

async function onSubmit(input: CreateDayInput, id?: number) {
  saving.value = true
  try {
    if (id === undefined) await daysApi.create(input)
    else await daysApi.update(id, input)
    formOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onRemove(id: number) {
  busy.value = true
  try {
    await daysApi.remove(id)
    formOpen.value = false
    await load()
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载日子…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="days-page">
    <!-- 页头：标题 + 新建 -->
    <div class="page-head">
      <div>
        <h1>倒数日</h1>
        <p class="page-sub">记住每一个重要的日子 · 倒数与纪念</p>
      </div>
      <Button size="sm" class="new-btn rounded-full px-4" @click="openCreate">
        <Plus class="size-4" />
        新建倒数日
      </Button>
    </div>

    <!-- 工具栏：筛选分段 + 摘要 -->
    <div class="toolbar">
      <Tabs v-model="filter">
        <TabsList class="seg">
          <TabsTrigger
            v-for="f in [
              { value: 'all', label: '全部' },
              { value: 'future', label: '倒数' },
              { value: 'memorial', label: '纪念日' },
            ]"
            :key="f.value"
            :value="f.value"
            class="h-auto px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
          >{{ f.label }}</TabsTrigger>
        </TabsList>
      </Tabs>
      <p v-if="days.length" class="summary">
        共 <b>{{ days.length }}</b> 个日子
        <template v-if="nearest"> · 最近的是 <b>{{ nearest.title }}</b>（还有 {{ nearest.daysUntil }} 天）</template>
      </p>
    </div>

    <!-- 卡片墙 -->
    <div v-if="filtered.length" class="card-wall">
      <DayCard v-for="d in filtered" :key="d.id" :day="d" @edit="openEdit" />
    </div>
    <div v-else class="placeholder empty"><div><p>这个分类下暂时没有日子</p></div></div>

    <!-- 新建 / 编辑弹窗 -->
    <DayDialog
      :open="formOpen"
      :saving="saving || busy"
      :editing="editing"
      @close="formOpen = false"
      @submit="onSubmit"
      @remove="onRemove"
    />
  </div>
</template>

<style scoped>
.days-page {
  max-width: var(--max-grid);
  margin: 0 auto;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}
.page-sub {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 0.9rem;
}
.new-btn {
  box-shadow: var(--sh-cta);
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
.summary {
  margin: 0;
  color: var(--text-3);
  font-size: 0.8rem;
}
.summary b {
  color: var(--text-2);
  font-weight: 700;
}

.card-wall {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.empty {
  margin-top: 18px;
}

@media (max-width: 860px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
