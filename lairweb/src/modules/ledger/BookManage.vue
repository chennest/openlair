<script setup lang="ts">
// 共享账本成员管理：成员列表（角色/移除）+ 添加成员（选已有用户或输入新名字）
import { ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import Tag from '../../components/Tag.vue'
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
}>()

const mode = ref<'list' | 'add'>('list')
const newName = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      mode.value = 'list'
      newName.value = ''
    }
  },
)

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
      <button v-if="mode === 'list'" class="btn-ghost" @click="mode = 'add'">＋ 添加成员</button>
      <button v-else class="btn-ghost" @click="mode = 'list'">‹ 返回</button>
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
  justify-content: flex-end;
  margin-top: 20px;
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
</style>
