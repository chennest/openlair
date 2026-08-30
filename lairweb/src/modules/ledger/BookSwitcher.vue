<script setup lang="ts">
// 账本切换器：当前账本下拉（个人/共享），共享账本显示成员头像；含新建账本入口
import { ref } from 'vue'
import { ChevronDown, Plus, Trash2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import type { Book } from './api'

const props = defineProps<{
  books: Book[]
  current: Book | null
}>()

const emit = defineEmits<{
  (e: 'switch', bookId: number): void
  (e: 'create'): void
  (e: 'manage', book: Book): void
  (e: 'join'): void
  (e: 'trash'): void
}>()

const open = ref(false)

function initials(name: string) {
  return name.slice(0, 1)
}

function pick(bookId: number) {
  open.value = false
  if (bookId !== props.current?.id) emit('switch', bookId)
}
</script>

<template>
  <div class="switcher">
    <Button
      variant="outline"
      class="justify-start gap-2.5 h-11 pl-[14px] pr-[14px] rounded-full! bg-white text-foreground text-[0.92rem] font-semibold cursor-pointer hover:border-primary"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="avatar" :class="{ shared: current?.type === 'shared' }" aria-hidden="true">
        {{ current ? initials(current.name) : '账' }}
      </span>
      <span class="name">{{ current?.name ?? '选择账本' }}</span>
      <ChevronDown class="chev" :class="open ? 'rotate-180' : 'rotate-0'" :size="16" aria-hidden="true" />
    </Button>

    <Transition name="pop">
      <div v-if="open" class="menu" role="listbox">
        <div class="menu-label">账本</div>
        <Button
          v-for="b in books"
          :key="b.id"
          variant="ghost"
          class="justify-start gap-2.5 w-full py-[9px] pl-[10px] pr-[10px] rounded-[var(--r-thumb)]! text-foreground text-[0.9rem] font-semibold cursor-pointer text-left transition-colors"
          :class="b.id === current?.id ? 'bg-[rgba(0,113,227,0.08)] hover:bg-primary/8' : ''"
          role="option"
          @click="pick(b.id)"
        >
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
        </Button>

        <div class="menu-actions">
          <Button variant="ghost" class="justify-start gap-1.5 py-[9px] pl-[10px] pr-[10px] rounded-[var(--r-thumb)]! text-primary text-[0.86rem] font-semibold cursor-pointer text-left hover:bg-primary/6 hover:text-primary" @click="open = false; emit('create')">
            <Plus class="size-4" />
            新建账本
          </Button>
          <Button variant="ghost" class="justify-start gap-1.5 py-[9px] pl-[10px] pr-[10px] rounded-[var(--r-thumb)]! text-primary text-[0.86rem] font-semibold cursor-pointer text-left hover:bg-primary/6 hover:text-primary" @click="open = false; emit('join')">
            <Plus class="size-4" />
            加入共享账本
          </Button>
          <Button v-if="current" variant="ghost" class="justify-start gap-1.5 py-[9px] pl-[10px] pr-[10px] rounded-[var(--r-thumb)]! text-primary text-[0.86rem] font-semibold cursor-pointer text-left hover:bg-primary/6 hover:text-primary" @click="open = false; emit('manage', current)">
            管理账本
          </Button>
          <Button variant="ghost" class="justify-start gap-1.5 py-[9px] pl-[10px] pr-[10px] rounded-[var(--r-thumb)]! text-[var(--text-3)] text-[0.86rem] font-semibold cursor-pointer text-left hover:bg-[var(--heat-bg)]! hover:text-[var(--heat)]!" @click="open = false; emit('trash')">
            <Trash2 class="size-4" />
            回收站
          </Button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.switcher {
  position: relative;
}
.chev {
  color: var(--text-3);
  transition: transform 200ms var(--ease-out-quart);
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
