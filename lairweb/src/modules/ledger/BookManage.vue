<script setup lang="ts">
// 共享账本成员管理：成员列表（角色/移除）+ 添加成员（选已有用户或输入新名字）+ 软删除
import { computed, onUnmounted, ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import Tag from '../../components/Tag.vue'
import { getUser } from '../../api/request'
import type { Book } from './api'

const props = defineProps<{
  open: boolean
  book: Book | null
  /** 可选添加的用户池（当前不是成员的人） */
  candidates: { id: number; name: string; avatarColor: string }[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'add', userId: number): void
  (e: 'addByName', name: string): void
  (e: 'remove', userId: number): void
  (e: 'delete'): void
  (e: 'convert'): void
}>()

const mode = ref<'list' | 'add'>('list')
const newName = ref('')

// 删除确认
const showDeleteConfirm = ref(false)
const deleteCountdown = ref(6)
const deleteNameInput = ref('')
let deleteTimer: ReturnType<typeof setInterval> | null = null

// 转为共享确认（3 秒倒计时，提示不可转回）
const showConvertConfirm = ref(false)
const convertCountdown = ref(3)
let convertTimer: ReturnType<typeof setInterval> | null = null

// 当前用户是否为 owner
const currentUserId = computed(() => {
  const u = getUser() as { id?: number } | null
  return u?.id ?? null
})
const isOwner = computed(() => {
  if (!currentUserId.value || !props.book) return false
  return props.book.members.find((m) => m.userId === currentUserId.value)?.role === 'owner'
})

function startCountdown() {
  deleteCountdown.value = 6
  if (deleteTimer) clearInterval(deleteTimer)
  deleteTimer = setInterval(() => {
    if (deleteCountdown.value > 0) deleteCountdown.value--
    else if (deleteTimer) clearInterval(deleteTimer)
  }, 1000)
}

function clearCountdown() {
  if (deleteTimer) {
    clearInterval(deleteTimer)
    deleteTimer = null
  }
}

function isDeleteConfirmReady() {
  return deleteCountdown.value === 0 && deleteNameInput.value.trim() === props.book?.name
}

function confirmDelete() {
  if (!isDeleteConfirmReady()) return
  emit('delete')
  showDeleteConfirm.value = false
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      mode.value = 'list'
      newName.value = ''
    }
  },
)

// 打开/关闭删除确认弹窗时重置
watch(showDeleteConfirm, (v) => {
  if (v) {
    deleteNameInput.value = ''
    startCountdown()
  } else {
    deleteNameInput.value = ''
    clearCountdown()
    deleteCountdown.value = 6
  }
})

// 转为共享确认：3 秒倒计时
function startConvertCountdown() {
  convertCountdown.value = 3
  if (convertTimer) clearInterval(convertTimer)
  convertTimer = setInterval(() => {
    if (convertCountdown.value > 0) convertCountdown.value--
    else if (convertTimer) clearInterval(convertTimer)
  }, 1000)
}

function clearConvertCountdown() {
  if (convertTimer) {
    clearInterval(convertTimer)
    convertTimer = null
  }
}

function confirmConvert() {
  if (convertCountdown.value > 0) return
  emit('convert')
  showConvertConfirm.value = false
}

watch(showConvertConfirm, (v) => {
  if (v) startConvertCountdown()
  else {
    clearConvertCountdown()
    convertCountdown.value = 3
  }
})

onUnmounted(() => {
  clearCountdown()
  clearConvertCountdown()
})

function addByName() {
  const n = newName.value.trim()
  if (!n) return
  emit('addByName', n)
  newName.value = ''
}

function initials(name: string) {
  return name.slice(0, 1)
}
</script>

<template>
  <BaseModal v-if="open && book" :title="`${book.name} · 成员`" @close="emit('close')">
    <div v-if="mode === 'list'" class="member-list">
      <div v-for="m in book.members" :key="m.userId" class="member">
        <span class="face" :style="{ background: m.user?.avatarColor ?? '#aeaeb2' }" aria-hidden="true">
          {{ m.user ? initials(m.user.name) : '?' }}
        </span>
        <span class="who">
          <span class="name">{{ m.user?.name ?? '未知' }}</span>
          <Tag :variant="m.role === 'owner' ? 'gold' : 'gray'">{{ m.role === 'owner' ? '拥有者' : '成员' }}</Tag>
        </span>
        <button v-if="m.role !== 'owner'" class="remove" @click="emit('remove', m.userId)">移除</button>
      </div>
    </div>

    <div v-else class="add-panel">
      <label class="label">从已有用户添加</label>
      <div class="cands">
        <button
          v-for="c in candidates"
          :key="c.id"
          class="cand"
          @click="emit('add', c.id)"
        >
          <span class="face" :style="{ background: c.avatarColor }">{{ initials(c.name) }}</span>
          {{ c.name }}
        </button>
        <p v-if="candidates.length === 0" class="none">没有可添加的用户了</p>
      </div>

      <label class="label">或输入新成员名字</label>
      <div class="row">
        <input
          v-model="newName"
          class="input"
          placeholder="成员昵称，如：爸爸"
          maxlength="12"
          @keyup.enter="addByName"
        />
        <button class="add-btn" :disabled="!newName.trim()" @click="addByName">添加</button>
      </div>
    </div>

    <div class="foot">
      <div class="foot-left">
        <button v-if="book.type === 'shared' && mode === 'list'" class="btn-ghost" @click="mode = 'add'">＋ 添加成员</button>
        <button v-if="book.type === 'shared' && mode === 'add'" class="btn-ghost" @click="mode = 'list'">‹ 返回</button>
        <button
          v-if="isOwner && book.type === 'personal' && mode === 'list'"
          class="btn-ghost"
          :title="'转为共享账本后可添加成员（不可再转回个人）'"
          @click="showConvertConfirm = true"
        >
          转为共享账本
        </button>
      </div>
      <button v-if="isOwner && mode === 'list'" class="btn-danger" @click="showDeleteConfirm = true">
        删除账本
      </button>
    </div>
  </BaseModal>

  <!-- 删除确认弹窗 -->
  <BaseModal v-if="showDeleteConfirm && book" title="删除账本" @close="showDeleteConfirm = false">
    <div class="delete-warn">
      <p class="warn-title">确定要删除「{{ book.name }}」吗？</p>
      <p class="warn-desc">
        账本及其所有流水、预算、成员将被移入回收站。可在回收站中恢复或彻底删除。
      </p>
    </div>

    <label class="label">输入账本名称以确认</label>
    <input
      v-model="deleteNameInput"
      class="input"
      :placeholder="`请输入「${book.name}」`"
      maxlength="20"
      @keyup.enter="confirmDelete()"
    />

    <div class="foot">
      <button class="btn-ghost" @click="showDeleteConfirm = false">取消</button>
      <button
        class="btn-primary-danger"
        :disabled="!isDeleteConfirmReady()"
        @click="confirmDelete()"
      >
        {{ deleteCountdown > 0 ? `${deleteCountdown}s 后可确认` : '确认删除' }}
      </button>
    </div>
  </BaseModal>

  <!-- 转为共享确认弹窗（3 秒倒计时，提示不可转回） -->
  <BaseModal v-if="showConvertConfirm && book" title="转为共享账本" @close="showConvertConfirm = false">
    <div class="convert-warn">
      <p class="warn-title">确定将「{{ book.name }}」转为共享账本吗？</p>
      <p class="warn-desc">
        转为共享账本后<strong>不可再转回个人账本</strong>，且其他成员可以查看并记账。请确认后继续。
      </p>
    </div>
    <div class="foot">
      <button class="btn-ghost" @click="showConvertConfirm = false">取消</button>
      <button class="btn-primary" :disabled="convertCountdown > 0" @click="confirmConvert()">
        {{ convertCountdown > 0 ? `${convertCountdown}s 后可确认` : '确认转为共享' }}
      </button>
    </div>
  </BaseModal>
</template>

<style scoped>
.member-list {
  display: flex;
  flex-direction: column;
}
.member {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--hairline);
}
.member:last-child {
  border-bottom: 0;
}
.face {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  flex: 0 0 auto;
}
.who {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
}
.remove {
  border: 0;
  border-radius: var(--r-pill);
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--heat);
  background: var(--heat-bg);
  cursor: pointer;
}
.add-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
}
.cands {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cand {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 160ms ease;
}
.cand:hover {
  border-color: var(--accent);
}
.cand .face {
  width: 20px;
  height: 20px;
  font-size: 10px;
}
.none {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-4);
}
.row {
  display: flex;
  gap: 8px;
}
.input {
  flex: 1;
  min-width: 0;
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
.add-btn {
  border: 0;
  border-radius: var(--r-pill);
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  cursor: pointer;
}
.add-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}
.foot-left {
  display: flex;
  gap: 10px;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--r-pill);
  color: var(--text);
  background: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: background 160ms ease;
}
.btn-ghost:hover {
  background: var(--hover);
}
/* 删除按钮（危险操作） */
.btn-danger {
  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--heat);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 160ms ease, transform 160ms ease;
}
.btn-danger:hover {
  opacity: 0.88;
}
/* 删除确认弹窗 */
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
  margin: 16px 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
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

.convert-warn {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 4px;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  padding: 0 20px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--accent);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 160ms ease;
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-primary:not(:disabled):hover {
  opacity: 0.88;
}
