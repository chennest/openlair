<script setup lang="ts">
// 四象限卡片（纯展示 + 勾选/删除）
import { computed } from 'vue'
import { Check, Trash2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { TodoItem } from './api'

const props = defineProps<{ title: string; items: TodoItem[] }>()

const emit = defineEmits<{
  (e: 'toggle', item: TodoItem): void
  (e: 'remove', id: number): void
}>()

/** 四象限颜色语义（token）：热力 / 强调 / 靛蓝 / 灰阶 */
const QUADRANT_COLORS: Record<string, string> = {
  重要紧急: 'var(--heat)',
  重要不紧急: 'var(--accent)',
  紧急不重要: 'var(--indigo)',
  不重要不紧急: 'var(--text-3)',
}
const dotColor = computed(() => QUADRANT_COLORS[props.title] ?? 'var(--text-3)')
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span class="title-label">
        <span class="q-dot" :style="{ background: dotColor }" aria-hidden="true"></span>
        <span>{{ title }}</span>
      </span>
      <Badge variant="secondary">{{ items.length }}</Badge>
    </div>
    <div class="row-list">
      <div v-for="item in items" :key="item.id" class="row">
        <label class="main">
          <input
            type="checkbox"
            class="check-input"
            :checked="item.done"
            @change="emit('toggle', item)"
          />
          <span class="check" :class="{ on: item.done }" aria-hidden="true">
            <Check v-if="item.done" class="size-3" :stroke-width="3" />
          </span>
          <span class="text" :class="{ done: item.done }">{{ item.text }}</span>
        </label>
        <span class="sub">
          <span class="due">{{ item.due }}</span>
          <Button
            variant="ghost"
            size="icon"
            class="del-btn"
            aria-label="删除任务"
            @click.stop="emit('remove', item.id)"
          >
            <Trash2 class="size-4" />
          </Button>
        </span>
      </div>
      <p v-if="items.length === 0" class="empty">暂无任务</p>
    </div>
  </article>
</template>

<style scoped>
.card {
  padding: 22px 22px 20px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: var(--text-2);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.title-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.q-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 999px;
}
.row-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
  min-height: 44px;
}
.row:last-child {
  border-bottom: 0;
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
  min-height: 36px;
  cursor: pointer;
}
.check-input {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  overflow: hidden;
  white-space: nowrap;
}
.check-input:focus-visible + .check {
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.28);
}
.check {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--text-4);
  border-radius: var(--r-chip);
  color: #fff;
  transition: border-color 160ms ease, background 160ms ease;
}
.check.on {
  border-color: var(--accent);
  background: var(--accent);
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.text.done {
  text-decoration: line-through;
  opacity: 0.5;
}
.sub {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-3);
}
.due {
  font-size: 0.78rem;
  color: var(--text-3);
}
.del-btn {
  color: var(--text-3);
}
.del-btn:hover {
  color: var(--heat);
  background: transparent;
}
.empty {
  margin: 6px 4px;
  color: var(--text-4);
  font-size: 0.84rem;
}

@media (max-width: 640px) {
  .del-btn {
    width: 44px;
    height: 44px;
  }
}
</style>
