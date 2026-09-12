<script setup lang="ts">
// 新建 / 编辑倒数日弹窗（基于 BaseModal；交互控件用 shadcn：Input / Tabs / Switch / Button）
import { ref, watch } from 'vue'
import { Trash2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import BaseModal from '../../components/BaseModal.vue'
import type { CreateDayInput, DayItem, DayRepeat } from './api'

const props = defineProps<{
  open: boolean
  saving: boolean
  /** null = 新建；非空 = 编辑该条（含删除入口） */
  editing: DayItem | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', input: CreateDayInput, id?: number): void
  (e: 'remove', id: number): void
}>()

const EMOJIS = ['🎂', '💍', '💕', '🎉', '📚', '🚀', '✈️', '🏠', '💰', '🎓', '🏅', '🕯️', '🐣', '🎄', '⭐', '🐱']
const REPEATS: { value: DayRepeat; label: string }[] = [
  { value: 'once', label: '一次性' },
  { value: 'yearly', label: '每年' },
  { value: 'monthly', label: '每月' },
]

const title = ref('')
const date = ref('')
const emoji = ref(EMOJIS[0]!)
const repeat = ref<DayRepeat>('once')
const pinned = ref(false)

/** 今天 YYYY-MM-DD（新建时的默认日期） */
function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 打开时按「新建 / 编辑」重置表单
watch(
  () => props.open,
  (open) => {
    if (!open) return
    const e = props.editing
    title.value = e?.title ?? ''
    date.value = e?.date ?? todayStr()
    emoji.value = e?.emoji || EMOJIS[0]!
    repeat.value = e?.repeat ?? 'once'
    pinned.value = e?.pinned ?? false
  },
)

function submit() {
  if (!title.value.trim() || !date.value) return
  emit('submit', { title: title.value.trim(), date: date.value, emoji: emoji.value, repeat: repeat.value, pinned: pinned.value }, props.editing?.id)
}
</script>

<template>
  <BaseModal v-if="open" :title="editing ? '编辑日子' : '新建倒数日'" @close="emit('close')">
    <div class="day-form">
      <Label class="text-[0.8rem] font-semibold text-[var(--text-2)]">图标</Label>
      <div class="emoji-grid" role="radiogroup" aria-label="选择图标">
        <button
          v-for="e in EMOJIS"
          :key="e"
          type="button"
          class="emoji-cell"
          :class="{ on: e === emoji }"
          @click="emoji = e"
        >
          {{ e }}
        </button>
      </div>

      <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">名称</Label>
      <Input v-model="title" class="h-11" placeholder="例如：结婚纪念日" maxlength="20" autofocus @keyup.enter="submit" />

      <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">日期</Label>
      <Input v-model="date" class="h-11 w-full" type="date" />

      <Label class="mt-2.5 text-[0.8rem] font-semibold text-[var(--text-2)]">重复规则</Label>
      <Tabs v-model="repeat">
        <TabsList class="seg">
          <TabsTrigger
            v-for="r in REPEATS"
            :key="r.value"
            :value="r.value"
            class="h-auto px-[14px] text-[13px] font-medium rounded-full text-[var(--text-2)] data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-semibold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
          >{{ r.label }}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div class="pin-row">
        <Label class="text-[0.8rem] font-semibold text-[var(--text-2)]">置顶显示</Label>
        <Switch v-model="pinned" aria-label="置顶显示" />
      </div>

      <div class="foot">
        <Button v-if="editing" variant="destructive" class="mr-auto" :disabled="saving" @click="emit('remove', editing.id)">
          <Trash2 class="size-4" />
          删除
        </Button>
        <Button variant="outline" @click="emit('close')">取消</Button>
        <Button :disabled="saving || !title.trim() || !date" @click="submit">
          {{ saving ? '保存中…' : editing ? '保存' : '创建' }}
        </Button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.day-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 6px;
}
.emoji-cell {
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  font-size: 1.15rem;
  line-height: 1;
  border: 1px solid transparent;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.035);
  transition: background 120ms ease, box-shadow 120ms ease;
}
.emoji-cell:hover {
  background: rgba(0, 0, 0, 0.08);
}
.emoji-cell.on {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.1);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.25);
}

/* 重复规则分段控件（同 LedgerFilter 的 iOS 分段样式） */
.seg {
  height: auto;
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--r-pill);
  padding: 3px;
  gap: 2px;
}

.pin-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
}
</style>
