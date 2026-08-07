<script setup lang="ts">
// 记账模块页：组装摘要/统计/表格/弹窗，负责数据加载与状态
import { onMounted, ref } from 'vue'
import { ledgerApi, type LedgerData } from './api'
import LedgerSummary from './LedgerSummary.vue'
import LedgerStats from './LedgerStats.vue'
import LedgerTable from './LedgerTable.vue'
import LedgerDialog from './LedgerDialog.vue'

const loading = ref(true)
const error = ref('')
const data = ref<LedgerData | null>(null)
const showDialog = ref(false)
const savedTip = ref(false)

async function load() {
  loading.value = true
  try {
    data.value = await ledgerApi.list()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate(payload: Parameters<typeof ledgerApi.create>[0]) {
  try {
    await ledgerApi.create(payload)
    showDialog.value = false
    savedTip.value = true
    setTimeout(() => (savedTip.value = false), 2000)
    await load()
  } finally {
    // 弹窗内 saving 状态由父组件提交完成后复位
  }
}

async function handleRemove(id: string) {
  await ledgerApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载账本…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="ledger">
    <!-- 顶部操作条 -->
    <div class="toolbar">
      <button class="add-btn" @click="showDialog = true">＋ 记一笔</button>
      <Transition name="fade">
        <span v-if="savedTip" class="saved-tip">✓ 已记录</span>
      </Transition>
    </div>

    <LedgerSummary v-if="data" :summary="data.summary" />

    <div class="lower-grid">
      <LedgerStats :stats="data?.categoryStats ?? []" />
      <LedgerTable :transactions="data?.transactions ?? []" @remove="handleRemove" />
    </div>

    <LedgerDialog :open="showDialog" @close="showDialog = false" @submit="handleCreate" />
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.add-btn {
  display: inline-flex;
  align-items: center;
  height: 44px;
  padding: 0 22px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--accent);
  font-weight: 600;
  font-size: 0.98rem;
  cursor: pointer;
  transition: transform 160ms var(--ease-out-quart), box-shadow 160ms var(--ease-out-quart);
}
.add-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--sh-cta);
}
.add-btn:active {
  transform: scale(0.97);
}
.saved-tip {
  color: var(--live);
  font-weight: 600;
  font-size: 0.9rem;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 240ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.lower-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 2fr;
  gap: 18px;
  margin-top: 18px;
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
@media (max-width: 960px) {
  .lower-grid {
    grid-template-columns: 1fr;
  }
}
</style>
