<script setup lang="ts">
// 共享账本管理：邀请码分享（owner）+ 成员列表（移除）+ 退出（成员）+ 转共享 + 软删除
import { computed, onUnmounted, ref, watch } from 'vue'
import { Check, Copy, Plus } from '@lucide/vue'
import BaseModal from '../../components/BaseModal.vue'
import Tag from '../../components/Tag.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getUser } from '../../api/request'
import type { Book } from './api'

const props = defineProps<{
  open: boolean
  book: Book | null
  /** 当前邀请码（owner 专属，由父组件拉取；null = 未生成） */
  inviteCode: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'remove', userId: number): void
  (e: 'delete'): void
  (e: 'convert'): void
  (e: 'reset-invite'): void
  (e: 'disable-invite'): void
  (e: 'leave'): void
}>()

// 删除确认
const showDeleteConfirm = ref(false)
const deleteCountdown = ref(6)
const deleteNameInput = ref('')
let deleteTimer: ReturnType<typeof setInterval> | null = null

// 转为共享确认（3 秒倒计时，提示不可转回）
const showConvertConfirm = ref(false)
const convertCountdown = ref(3)
let convertTimer: ReturnType<typeof setInterval> | null = null

// 邀请码：复制反馈 / 重置确认 / 关闭确认
const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null
const confirmReset = ref(false)
const confirmDisable = ref(false)

// 当前用户是否为 owner
const currentUserId = computed(() => {
  const u = getUser() as { id?: number } | null
  return u?.id ?? null
})
const isOwner = computed(() => {
  if (!currentUserId.value || !props.book) return false
  return props.book.members.find((m) => m.userId === currentUserId.value)?.role === 'owner'
})
const formattedCode = computed(() => {
  const c = props.inviteCode ?? ''
  return c.length > 4 ? `${c.slice(0, 4)}-${c.slice(4)}` : c
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
      copied.value = false
      confirmReset.value = false
      confirmDisable.value = false
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
  if (copyTimer) clearTimeout(copyTimer)
})

async function copyCode() {
  if (!props.inviteCode) return
  try {
    await navigator.clipboard.writeText(props.inviteCode)
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => (copied.value = false), 1600)
  } catch {
    /* 剪贴板不可用则忽略 */
  }
}

function doResetInvite() {
  confirmReset.value = false
  emit('reset-invite')
}

function doDisableInvite() {
  confirmDisable.value = false
  emit('disable-invite')
}

function initials(name: string) {
  return name.slice(0, 1)
}
</script>

<template>
  <BaseModal v-if="open && book" :title="`${book.name} · 成员`" @close="emit('close')">
    <!-- 邀请码分享（仅 owner + 共享账本） -->
    <section v-if="isOwner && book.type === 'shared'" class="invite">
      <p class="section-title">邀请成员</p>
      <p class="section-desc">邀请码就是账本的「钥匙」，对方输入即可加入共享账本。</p>

      <div v-if="inviteCode" class="code-box">
        <span class="code" aria-label="邀请码">{{ formattedCode }}</span>
        <Button size="sm" @click="copyCode">
          <Check v-if="copied" class="size-3.5" />
          <Copy v-else class="size-3.5" />
          {{ copied ? '已复制' : '复制' }}
        </Button>
      </div>
      <Button v-else size="sm" @click="emit('reset-invite')">
        <Plus class="size-3.5" />
        生成邀请码
      </Button>

      <div v-if="inviteCode" class="invite-actions">
        <template v-if="!confirmReset && !confirmDisable">
          <Button variant="ghost" size="sm" class="btn-link" @click="confirmReset = true">重置邀请码</Button>
          <Button variant="ghost" size="sm" class="btn-link danger" @click="confirmDisable = true">关闭邀请</Button>
        </template>
        <template v-else-if="confirmReset">
          <span class="confirm-hint">重置后旧码立即失效</span>
          <Button size="sm" class="btn-primary-sm" @click="doResetInvite">确认重置</Button>
          <Button variant="ghost" size="sm" class="btn-link" @click="confirmReset = false">取消</Button>
        </template>
        <template v-else-if="confirmDisable">
          <span class="confirm-hint">关闭后无法再被加入</span>
          <Button size="sm" class="btn-primary-sm" @click="doDisableInvite">确认关闭</Button>
          <Button variant="ghost" size="sm" class="btn-link" @click="confirmDisable = false">取消</Button>
        </template>
      </div>
    </section>

    <!-- 成员列表 -->
    <p class="section-title">成员（{{ book.members.length }}）</p>
    <div class="member-list">
      <div v-for="m in book.members" :key="m.userId" class="member">
        <span class="face" :style="{ background: m.user?.avatarColor ?? '#aeaeb2' }" aria-hidden="true">
          {{ m.user ? initials(m.user.name) : '?' }}
        </span>
        <span class="who">
          <span class="name">
            {{ m.user?.name ?? '未知' }}
            <span v-if="m.userId === currentUserId" class="me">(我)</span>
          </span>
          <Tag :variant="m.role === 'owner' ? 'gold' : 'gray'">{{ m.role === 'owner' ? '拥有者' : '成员' }}</Tag>
        </span>
        <Button v-if="isOwner && m.role !== 'owner'" size="sm" variant="destructive" class="remove" @click="emit('remove', m.userId)">移除</Button>
      </div>
    </div>

    <div class="foot">
      <div class="foot-left">
        <Button
          v-if="isOwner && book.type === 'personal'"
          variant="outline"
          class="btn-ghost"
          :title="'转为共享账本后可邀请成员（不可再转回个人）'"
          @click="showConvertConfirm = true"
        >
          转为共享账本
        </Button>
        <Button v-if="!isOwner" variant="outline" class="btn-ghost" @click="emit('leave')">退出账本</Button>
      </div>
      <Button
        v-if="isOwner"
        variant="destructive"
        class="bg-destructive text-white hover:bg-destructive/90"
        @click="showDeleteConfirm = true"
      >
        删除账本
      </Button>
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

    <Label class="label">输入账本名称以确认</Label>
    <Input
      v-model="deleteNameInput"
      class="input"
      :placeholder="`请输入「${book.name}」`"
      maxlength="20"
      @keyup.enter="confirmDelete()"
    />

    <div class="foot">
      <Button variant="outline" class="btn-ghost" @click="showDeleteConfirm = false">取消</Button>
      <Button
        variant="destructive"
        class="bg-destructive text-white hover:bg-destructive/90"
        :disabled="!isDeleteConfirmReady()"
        @click="confirmDelete()"
      >
        {{ deleteCountdown > 0 ? `${deleteCountdown}s 后可确认` : '确认删除' }}
      </Button>
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
      <Button variant="outline" class="btn-ghost" @click="showConvertConfirm = false">取消</Button>
      <Button class="btn-primary" :disabled="convertCountdown > 0" @click="confirmConvert()">
        {{ convertCountdown > 0 ? `${convertCountdown}s 后可确认` : '确认转为共享' }}
      </Button>
    </div>
  </BaseModal>
</template>

<style scoped>
.section-title {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.02em;
}
.section-desc {
  margin: 0 0 12px;
  font-size: 0.82rem;
  color: var(--text-3);
  line-height: 1.5;
}
/* 邀请码展示 */
.invite {
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--hairline);
}
.code-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  background: var(--bg);
  margin-bottom: 8px;
}
.code {
  flex: 1;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.invite-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  min-height: 32px;
}
.btn-link {
  height: auto;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-link.danger {
  color: var(--heat);
}
.btn-link:hover {
  text-decoration: underline;
  color: var(--accent);
  background: transparent;
}
.btn-link.danger:hover {
  color: var(--heat);
}
.confirm-hint {
  font-size: 12px;
  color: var(--heat);
  font-weight: 600;
}
.btn-primary-sm {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--r-pill);
  font-size: 12.5px;
  font-weight: 600;
}
/* 成员列表 */
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
.me {
  font-weight: 500;
  color: var(--text-3);
  font-size: 0.8rem;
}
.remove {
  height: auto;
  border-radius: var(--r-pill);
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 600;
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
.input {
  width: 100%;
  height: 42px;
  box-sizing: border-box;
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
  border-radius: var(--r-pill);
  font-weight: 600;
  font-size: 13px;
}
</style>
