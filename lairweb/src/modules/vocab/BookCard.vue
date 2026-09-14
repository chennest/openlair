<script setup lang="ts">
// 词书卡片：进度条 + 待复习徽标 + 四模式入口；用户级词书带「我的」徽标和删除入口
import { computed } from 'vue'
import { BookOpen, Trash2 } from '@lucide/vue'
import { VOCAB_MODES, type VocabBook, type VocabMode } from './api'

const props = defineProps<{ book: VocabBook; canDelete: boolean }>()
const emit = defineEmits<{ practice: [mode: VocabMode]; delete: [bookId: number] }>()

const learned = computed(() => props.book.learning + props.book.mastered)
const percent = computed(() => (props.book.wordCount ? Math.round((learned.value / props.book.wordCount) * 100) : 0))

function onDelete() {
  if (window.confirm(`确定删除词书「${props.book.name}」吗？学习进度会保留。`)) {
    emit('delete', props.book.id)
  }
}
</script>

<template>
  <div class="book-card">
    <div class="book-head">
      <span class="book-emoji">{{ book.emoji || '📖' }}</span>
      <div class="book-title">
        <h3>
          {{ book.name }}
          <span v-if="book.ownerId !== null" class="mine-badge">我的</span>
        </h3>
        <p class="book-desc">{{ book.description || `${book.wordCount} 个单词` }}</p>
      </div>
      <button
        v-if="canDelete"
        class="del-btn"
        type="button"
        aria-label="删除词书"
        @click="onDelete"
      >
        <Trash2 class="size-4" />
      </button>
    </div>

    <div class="book-progress">
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${percent}%` }" />
      </div>
      <div class="progress-nums">
        <span>已学 <b>{{ learned }}</b> / {{ book.wordCount }}</span>
        <span v-if="book.due" class="due-badge">待复习 {{ book.due }}</span>
      </div>
    </div>

    <div class="mode-row">
      <button v-for="m in VOCAB_MODES" :key="m.value" class="mode-btn" type="button" @click="emit('practice', m.value)">
        <BookOpen class="size-3.5" />
        {{ m.label }}
      </button>
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
  transition: transform 0.25s var(--ease-out-quart), box-shadow 0.25s var(--ease-out-quart);
}
.book-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--sh-lift);
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
.book-title h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}
.mine-badge {
  flex: none;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 600;
}
.del-btn {
  flex: none;
  margin-left: auto;
  display: inline-flex;
  padding: 7px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.del-btn:hover {
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.08);
}
.del-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.book-desc {
  margin: 3px 0 0;
  color: var(--text-3);
  font-size: 0.8rem;
}

.progress-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: width 0.4s var(--ease-out-quart);
}
.progress-nums {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
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
.mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 0;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  background: transparent;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-2);
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.mode-btn:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.mode-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
