<script setup lang="ts">
// 词书卡片：进度条 + 待复习徽标 + 四模式入口；用户级词书带「我的」徽标和删除入口
// 点整卡进词书详情页（模式按钮与删除按钮阻止冒泡，保持原行为）
import { computed } from 'vue'
import { BookOpen, Trash2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { tone } from './status'
import { VOCAB_MODES, type VocabBook, type VocabMode } from './api'

const props = defineProps<{ book: VocabBook; canDelete: boolean }>()
const emit = defineEmits<{
  practice: [mode: VocabMode]
  delete: [bookId: number]
  open: [bookId: number]
}>()

const learned = computed(() => props.book.learning + props.book.mastered)
const percent = computed(() => (props.book.wordCount ? Math.round((learned.value / props.book.wordCount) * 100) : 0))

function onDelete() {
  if (window.confirm(`确定删除词书「${props.book.name}」吗？学习进度会保留。`)) {
    emit('delete', props.book.id)
  }
}
</script>

<template>
  <div
    class="book-card"
    role="button"
    tabindex="0"
    :aria-label="`查看词书 ${book.name}`"
    @click="emit('open', book.id)"
    @keydown.enter="emit('open', book.id)"
  >
    <div class="book-head">
      <span class="book-emoji">{{ book.emoji || '📖' }}</span>
      <div class="book-title">
        <h3>{{ book.name }}</h3>
        <p class="book-desc">{{ book.description || `${book.wordCount} 个单词` }}</p>
      </div>
      <Badge v-if="book.ownerId !== null" variant="ghost" :class="tone('blue')">我的</Badge>
      <Button
        v-if="canDelete"
        variant="ghost"
        size="icon-sm"
        class="ml-auto text-[var(--text-3)] hover:bg-transparent hover:text-[var(--destructive)]"
        aria-label="删除词书"
        @click.stop="onDelete"
      >
        <Trash2 class="size-4" />
      </Button>
    </div>

    <div class="book-progress">
      <Progress :model-value="percent" class="bg-[var(--track)]" aria-label="词书学习进度" />
      <div class="progress-nums">
        <span>已学 <b>{{ learned }}</b> / {{ book.wordCount }}</span>
        <span v-if="book.due" class="due-badge">待复习 {{ book.due }}</span>
      </div>
    </div>

    <div class="mode-row">
      <Button
        v-for="m in VOCAB_MODES"
        :key="m.value"
        variant="outline"
        size="sm"
        class="w-full rounded-full text-[var(--text-2)]"
        @click.stop="emit('practice', m.value)"
      >
        <BookOpen class="size-3.5" />
        {{ m.label }}
      </Button>
    </div>
  </div>
</template>

<style scoped>
.book-card {
  background: var(--surface);
  border-radius: var(--r-card);
  box-shadow: var(--sh-card);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  cursor: pointer;
  transition: transform 0.25s var(--ease-out-quart), box-shadow 0.25s var(--ease-out-quart);
}
.book-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--sh-lift);
}
.book-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.book-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.book-emoji {
  font-size: 2rem;
  line-height: 1;
}
.book-title {
  min-width: 0;
}
.book-title h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.book-desc {
  margin: 3px 0 0;
  color: var(--text-3);
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.progress-nums {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.78rem;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.progress-nums b {
  color: var(--text-2);
}
.due-badge {
  color: var(--heat);
  font-weight: 600;
}

.mode-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
</style>
