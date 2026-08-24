<script setup lang="ts">
// API Key 管理页：创建（明文仅展示一次）+ 列表 + 撤销
import { onMounted, ref } from 'vue'
import { Copy, KeyRound, Plus, Trash2, X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiKeyApi, type ApiKeyItem } from './api'

// ---------- 三态：loading / error / data ----------
const loading = ref(true)
const error = ref('')
const keys = ref<ApiKeyItem[]>([])

const newName = ref('')
const saving = ref(false)

/** 创建成功但还未“确认已保存”的明文（仅此刻存在内存，刷新即消失） */
const pendingKey = ref<{ name: string; key: string } | null>(null)
const copied = ref(false)

async function load() {
  loading.value = true
  try {
    keys.value = (await apiKeyApi.list()).keys
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createKey() {
  if (!newName.value.trim() || saving.value) return
  saving.value = true
  try {
    const data = await apiKeyApi.create(newName.value.trim())
    newName.value = ''
    copied.value = false
    pendingKey.value = { name: data.item.name, key: data.apiKey }
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

async function copyKey() {
  if (!pendingKey.value) return
  await navigator.clipboard.writeText(pendingKey.value.key)
  copied.value = true
}

function dismissPending() {
  pendingKey.value = null
  copied.value = false
}

async function revokeKey(id: number) {
  await apiKeyApi.remove(id)
  await load()
}

function fmt(stamp: string | null) {
  if (!stamp) return '从未使用'
  const d = new Date(stamp)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="placeholder"><div><p>正在加载 API Key…</p></div></div>
  <div v-else-if="error" class="placeholder"><div><p class="symbol">!</p><p>{{ error }}</p></div></div>

  <div v-else class="keys-page">
    <h1 class="page-title">API Keys</h1>
    <p class="page-sub">创建长期访问凭证供 MCP / 脚本 / 第三方客户端使用，等价于你的登录身份，可随时撤销。</p>

    <!-- 创建 -->
    <form class="composer" @submit.prevent="createKey">
      <div class="composer-field">
        <KeyRound class="composer-icon" />
        <Input
          v-model="newName"
          class="h-11 min-w-0 flex-1 rounded-[var(--r-thumb)]"
          placeholder="名称，如：我的 MCP 客户端"
          maxlength="30"
        />
      </div>
      <Button type="submit" :disabled="saving" class="h-11 min-w-[130px] rounded-full px-[18px] font-semibold max-[860px]:w-full">
        <Plus class="size-4" />
        {{ saving ? '创建中…' : '创建 API Key' }}
      </Button>
    </form>

    <!-- 创建成功：明文只展示一次 -->
    <div v-if="pendingKey" class="pending-panel">
      <div class="pending-head">
        <span class="pending-title">已创建「{{ pendingKey.name }}」</span>
        <button class="close-btn" type="button" aria-label="关闭" @click="dismissPending">
          <X class="size-4" />
        </button>
      </div>
      <div class="key-plain">
        <code>{{ pendingKey.key }}</code>
        <Button size="sm" variant="outline" class="copy-btn" @click="copyKey">
          <Copy class="size-3.5" />
          {{ copied ? '已复制' : '复制' }}
        </Button>
      </div>
      <p class="pending-warn">请立即保存此 Key，关闭后无法再次查看明文。</p>
    </div>

    <!-- 列表：统一面板 + hairline 分割 -->
    <div v-if="keys.length" class="panel-list">
      <div v-for="k in keys" :key="k.id" class="panel-row">
        <div class="row-main">
          <span class="row-name">{{ k.name }}</span>
          <span class="row-prefix">{{ k.prefix }}…</span>
        </div>
        <div class="row-meta">
          <span>创建于 {{ fmt(k.createdAt) }}</span>
          <span>最近使用 {{ fmt(k.lastUsedAt) }}</span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          class="revoke-btn"
          @click="revokeKey(k.id)"
        >
          <Trash2 class="size-3.5" />
          撤销
        </Button>
      </div>
    </div>
    <p v-else class="empty-hint">还没有 API Key，先创建一个试试。</p>
  </div>
</template>

<style scoped>
.page-title {
  margin: 0 0 8px;
  font-size: clamp(27px, 5vw, 46px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
}
.page-sub {
  margin: 0 0 clamp(24px, 4vw, 34px);
  color: var(--text-2);
  font-size: 15px;
  line-height: 1.6;
}

.composer {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  padding: 14px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.composer-field {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}
.composer-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: var(--text-3);
  pointer-events: none;
}
.composer-field :deep(.input) {
  padding-left: 36px;
}

.pending-panel {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.pending-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.pending-title {
  font-size: 14px;
  font-weight: 600;
}
.close-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: var(--track);
  color: var(--text-2);
  cursor: pointer;
}
.key-plain {
  display: flex;
  align-items: center;
  gap: 10px;
}
.key-plain code {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding: 10px 12px;
  border-radius: var(--r-thumb);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  white-space: nowrap;
}
.copy-btn {
  flex: 0 0 auto;
}
.pending-warn {
  margin: 10px 0 0;
  color: var(--heat);
  font-size: 13px;
}

.panel-list {
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
  overflow: hidden;
}
.panel-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
}
.panel-row + .panel-row {
  border-top: 1px solid var(--hairline);
}
.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.row-name {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-prefix {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--text-3);
}
.row-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: right;
  color: var(--text-3);
  font-size: 12.5px;
  flex: 0 0 auto;
}
.revoke-btn {
  flex: 0 0 auto;
  color: var(--heat);
}

.empty-hint {
  margin: 28px 0;
  text-align: center;
  color: var(--text-3);
  font-size: 14px;
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

@media (max-width: 860px) {
  .composer {
    flex-direction: column;
  }
  .panel-row {
    flex-wrap: wrap;
    gap: 10px;
  }
  .row-meta {
    width: 100%;
    flex-direction: row;
    justify-content: space-between;
    text-align: left;
  }
  .revoke-btn {
    margin-left: auto;
  }
}
</style>
