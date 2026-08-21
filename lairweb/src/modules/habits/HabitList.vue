<script setup lang="ts">
// 习惯列表（纯展示 + 打卡/删除）
import { Check, Flame, RotateCcw, Trash2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { Habit } from './api'

defineProps<{ habits: Habit[] }>()

const emit = defineEmits<{
  (e: 'toggle', habit: Habit): void
  (e: 'remove', id: number): void
}>()
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>习惯打卡</span>
      <span class="tag green">{{ habits.length }} 项</span>
    </div>
    <div class="row-list">
      <div v-for="h in habits" :key="h.id" class="row habit-row">
        <div class="main">
          <span class="streak" :title="`已连续打卡 ${h.streak} 天`">
            <Flame class="size-4" aria-hidden="true" />
            <span>{{ h.streak }}</span>
          </span>
          <span class="text">{{ h.name }}</span>
        </div>

        <div class="progress-wrap">
          <span class="progress-label">{{ h.week.filter((d) => d).length }}/7 天</span>
          <Progress
            :model-value="(h.week.filter((d) => d).length / 7) * 100"
            class="progress-bar bg-[var(--track)]"
            aria-label="本周完成度"
          />
        </div>

        <Button
          size="sm"
          class="check-btn rounded-full"
          :class="h.done ? 'bg-[var(--live)] text-white hover:bg-[var(--live)]/85' : ''"
          @click="emit('toggle', h)"
        >
          <Check v-if="!h.done" class="size-4" />
          <RotateCcw v-else class="size-4" />
          {{ h.done ? '取消' : '打卡' }}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          class="del-btn rounded-full text-[var(--text-3)] hover:bg-destructive/10 hover:text-destructive"
          :title="`删除「${h.name}」`"
          aria-label="删除习惯"
          @click="emit('remove', h.id)"
        >
          <Trash2 class="size-4" />
        </Button>
      </div>
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
.tag {
  flex: 0 0 auto;
  padding: 3px 10px;
  border-radius: var(--r-pill);
  font-size: 0.72rem;
  font-weight: 600;
  color: #0a5a2c;
  background: rgba(48, 209, 88, 0.16);
}
.row-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.9rem;
}
.row:last-child {
  border-bottom: 0;
}
.habit-row {
  padding: 12px 4px;
}
.main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.streak {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-2);
  font-weight: 700;
  font-size: 0.86rem;
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
}
.streak svg {
  color: var(--heat);
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.progress-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  flex: 0 0 auto;
  min-width: 96px;
}
.progress-label {
  color: var(--text-3);
  font-size: 0.72rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.progress-bar {
  width: 96px;
}
.check-btn {
  min-width: 76px;
  min-height: 36px;
  padding-inline: 16px;
}
.del-btn {
  flex: 0 0 auto;
}

@media (max-width: 860px) {
  .habit-row {
    flex-wrap: wrap;
    row-gap: 10px;
  }
  .main {
    flex: 1 1 100%;
  }
  .progress-wrap {
    flex: 1;
    align-items: stretch;
    min-width: 0;
  }
  .progress-bar {
    width: 100%;
  }
  .check-btn {
    min-height: 44px;
  }
  .del-btn {
    min-height: 44px;
    min-width: 44px;
  }
}
</style>
