<script setup lang="ts">
// 账本回收站：显示已删除的账本，支持恢复或彻底删除
import { onUnmounted, ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import type { Book } from './api'

const props = defineProps<{
  open: boolean
  books: Book[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'restore', bookId: number): void
  (e: 'purge', bookId: number): void
}>()

// 彻底删除确认
const purgeTarget = ref<Book | null>(null)
const purgeCountdown = ref(6)
const purgeNameInput = ref('')
let purgeTimer: ReturnType<typeof setInterval> | null = null

function formatDate(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function startPurgeCountdown() {
  purgeCountdown.value = 6
  if (purgeTimer) clearInterval(purgeTimer)
  purgeTimer = setInterval(() => {
    if (purgeCountdown.value > 0) purgeCountdown.value--
    else if (purgeTimer) clearInterval(purgeTimer)
  }, 1000)
}

function clearPurgeTimer() {
  if (purgeTimer) {
    clearInterval(purgeTimer)
    purgeTimer = null
  }
}

onUnmounted(clearPurgeTimer)

function isPurgeReady() {
  return purgeCountdown.value === 0 && purgeNameInput.value.trim() === purgeTarget.value?.name
}

function confirmPurge() {
  if (!isPurgeReady() || !purgeTarget.value) return
  emit('purge', purgeTarget.value.id)
  purgeTarget.value = null
}

function openPurge(book: Book) {
  purgeTarget.value = book
}

// 关闭弹窗 / purge 确认时重置
watch(
  () => props.open,
  (v) => {
    if (!v) closePurge()
  },
)

function closePurge() {
  purgeTarget.value = null
  purgeNameInput.value = ''
  clearPurgeTimer()
  purgeCountdown.value = 6
}

watch(purgeTarget, (v) => {
  if (v) {
    purgeNameInput.value = ''
    startPurgeCountdown()
  }
})
</script>

<template>
  <BaseModal v-if="open" title="回收站" @close="emit('close')">
    <div v-if="books.length === 0" class="empty">
      <p>回收站为空</p>
    </div>

    <div v-else class="trash-list">
      <div v-for="b in books" :key="b.id" class="trash-item">
        <div class="trash-info">
          <span class="trash-name">{{ b.name }}</span>
          <span class="trash-meta">
            删除于 {{ formatDate(b.deletedAt) }} · {{ b.members.length }} 人
          </span>
        </div>
        <div class="trash-actions">
          <button class="btn-restore" @click="emit('restore', b.id)">恢复</button>
          <button class="btn-purge" @click="openPurge(b)">彻底删除（不可恢复）</button>
        </div>
      </div>
    </div>
  </BaseModal>

  <!-- 彻底删除确认弹窗 -->
  <BaseModal v-if="purgeTarget" title="彻底删除" @close="closePurge">
    <div class="delete-warn">
      <p class="warn-title">确定要彻底删除「{{ purgeTarget.name }}」吗？</p>
      <p class="warn-desc">
        此操作不可恢复。账本及其所有流水、预算、成员数据将被永久删除。
      </p>
    </div>

    <label class="label">输入账本名称以确认</label>
    <input
      v-model="purgeNameInput"
      class="input"
      :placeholder="`请输入「${purgeTarget.name}」`"
      maxlength="20"
      @keyup.enter="confirmPurge()"
    />

    <div class="foot">
      <button class="btn-ghost" @click="closePurge">取消</button>
      <button
        class="btn-primary-danger"
        :disabled="!isPurgeReady()"
        @click="confirmPurge()"
      >
        {{ purgeCountdown > 0 ? `${purgeCountdown}s 后可确认` : '确认彻底删除' }}
      </button>
    </div>
  </BaseModal>
</template>

<style scoped>
/* 空状态 */
.empty {
  padding: 30px 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.92rem;
}

/* 回收站列表 */
.trash-list {
  display: flex;
  flex-direction: column;
}
.trash-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--hairline);
}
.trash-item:last-child {
  border-bottom: 0;
}
.trash-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.trash-name {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.trash-meta {
  font-size: 12px;
  color: var(--text-3);
}
.trash-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.btn-restore {
  border: 0;
  border-radius: var(--r-pill);
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  cursor: pointer;
  transition: opacity 160ms ease;
}
.btn-restore:hover {
  opacity: 0.88;
}
.btn-purge {
  border: 0;
  border-radius: var(--r-pill);
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--heat);
  background: var(--heat-bg);
  cursor: pointer;
  transition: opacity 160ms ease;
}
.btn-purge:hover {
  opacity: 0.75;
}

/* 彻底删除确认弹窗 */
.delete-warn {
  margin-bottom: 16px;
}
.warn-title {
  margin: 0 0 6px;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
}
.warn-desc {
  margin: 0;
  font-size: 0.86rem;
  color: var(--text-2);
  line-height: 1.55;
}
.label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
}
.input {
  width: 100%;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  padding: 10px 12px;
  font-size: 0.92rem;
  color: var(--text);
  background: var(--surface);
  outline: none;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  height: 44px;
  padding: 0 19px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--r-pill);
  color: var(--text);
  background: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  cursor: pointer;
  transition: background 160ms ease;
}
.btn-ghost:hover {
  background: var(--hover);
}
.btn-primary-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  padding: 0 20px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--heat);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 160ms ease;
}
.btn-primary-danger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-primary-danger:not(:disabled):hover {
  opacity: 0.88;
}
</style>
