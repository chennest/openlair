<script setup lang="ts">
// 账本切换器：当前账本下拉（个人/共享），共享账本显示成员头像；含新建账本入口
import { ref } from 'vue'
import type { Book } from './api'

const props = defineProps<{
  books: Book[]
  current: Book | null
}>()

const emit = defineEmits<{
  (e: 'switch', bookId: string): void
  (e: 'create'): void
  (e: 'manage', book: Book): void
}>()

const open = ref(false)

function initials(name: string) {
  return name.slice(0, 1)
}

function pick(bookId: string) {
  open.value = false
  if (bookId !== props.current?.id) emit('switch', bookId)
}
</script>

<template>
  <div class="switcher">
    <button class="trigger" @click="open = !open" aria-haspopup="listbox" :aria-expanded="open">
      <span class="avatar" :class="{ shared: current?.type === 'shared' }" aria-hidden="true">
        {{ current ? initials(current.name) : '账' }}
      </span>
      <span class="name">{{ current?.name ?? '选择账本' }}</span>
      <svg class="chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6 9l6 6 6-6" />
      </svg>
    </button>

    <Transition name="pop">
      <div v-if="open" class="menu" role="listbox">
        <div class="menu-label">账本</div>
        <button v-for="b in books" :key="b.id" class="item" :class="{ on: b.id === current?.id }" role="option" @click="pick(b.id)">
          <span class="avatar" :class="{ shared: b.type === 'shared' }" aria-hidden="true">{{ initials(b.name) }}</span>
          <span class="item-name">
            <span>{{ b.name }}</span>
            <span class="meta">
              {{ b.type === 'shared' ? `共享 · ${b.members.length} 人` : '个人' }}
            </span>
          </span>
          <span v-if="b.type === 'shared'" class="faces" aria-hidden="true">
            <span
              v-for="m in b.members.slice(0, 4)"
              :key="m.userId"
              class="face"
              :style="{ background: m.user?.avatarColor ?? '#aeaeb2' }"
            >{{ m.user ? m.user.name.slice(0, 1) : '?' }}</span>
          </span>
        </button>

        <div class="menu-actions">
          <button class="act" @click="open = false; emit('create')">＋ 新建账本</button>
          <button v-if="current && current.type === 'shared'" class="act" @click="open = false; emit('manage', current)">
            管理成员
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.switcher {
  position: relative;
}
.trigger {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  background: var(--surface);
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.trigger:hover {
  border-color: var(--accent);
}
.chev {
  color: var(--text-3);
  transition: transform 200ms var(--ease-out-quart);
}
.trigger[aria-expanded='true'] .chev {
  transform: rotate(180deg);
}
.avatar {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: var(--text);
}
.avatar.shared {
  background: var(--accent);
}
.menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 60;
  width: 280px;
  padding: 8px;
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-overlay);
}
.menu-label {
  padding: 6px 10px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.04em;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: var(--r-thumb);
  background: transparent;
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease;
}
.item:hover {
  background: var(--hover);
}
.item.on {
  background: rgba(0, 113, 227, 0.08);
}
.item-name {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.meta {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-3);
}
.faces {
  display: flex;
  align-items: center;
}
.face {
  width: 20px;
  height: 20px;
  margin-left: -6px;
  border-radius: 50%;
  border: 2px solid var(--surface);
  display: grid;
  place-items: center;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
}
.face:first-child {
  margin-left: 0;
}
.menu-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid var(--hairline);
}
.act {
  padding: 9px 10px;
  border: 0;
  border-radius: var(--r-thumb);
  background: transparent;
  color: var(--accent);
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease;
}
.act:hover {
  background: rgba(0, 113, 227, 0.06);
}
.pop-enter-active,
.pop-leave-active {
  transition: opacity 160ms ease, transform 160ms var(--ease-out-quart);
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@media (prefers-reduced-motion: reduce) {
  .pop-enter-active,
  .pop-leave-active {
    transition: opacity 160ms ease;
    transform: none !important;
  }
}
</style>
