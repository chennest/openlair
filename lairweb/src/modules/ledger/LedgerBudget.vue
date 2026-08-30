<script setup lang="ts">
// 预算卡：本月预算 + 已用 + 剩余 + meter（灰轨道 + accent 填充，超支转 heat）
// 内联编辑：点「调整」切换输入框
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const props = defineProps<{
  budget: number
  expense: number
}>()

const emit = defineEmits<{
  (e: 'save', amount: number): void
}>()

const editing = ref(false)
const draft = ref('')

const percent = computed(() => (props.budget > 0 ? Math.min(100, (props.expense / props.budget) * 100) : 0))
const over = computed(() => props.budget > 0 && props.expense > props.budget)
const left = computed(() => Number((props.budget - props.expense).toFixed(2)))

function startEdit() {
  draft.value = String(props.budget)
  editing.value = true
}

function save() {
  const n = Number(draft.value)
  if (Number.isFinite(n) && n >= 0) emit('save', n)
  editing.value = false
}

function cancel() {
  editing.value = false
}
</script>

<template>
  <article class="card">
    <div class="card-title">
      <span>本月预算</span>
      <Button v-if="!editing" variant="ghost" size="sm" class="h-auto text-[12px] font-semibold text-primary bg-transparent py-1 pl-2 pr-2 rounded-full! hover:bg-primary/6" @click="startEdit">调整</Button>
    </div>

    <div v-if="editing" class="editor">
      <Input
        v-model="draft"
        type="number"
        min="0"
        step="100"
        class="flex-1 min-w-0 h-9 px-3 py-[9px] border-[var(--hairline)]! rounded-[var(--r-thumb)]! text-foreground bg-white shadow-none! text-[1rem] md:text-[1rem]"
        autofocus
        @keyup.enter="save"
        @keyup.esc="cancel"
      />
      <Button size="sm" @click="save">保存</Button>
      <Button variant="outline" size="sm" @click="cancel">取消</Button>
    </div>

    <template v-else>
      <div class="top">
        <span class="used num">已用 ¥{{ Number(expense).toFixed(2) }}</span>
        <span class="budget num">预算 ¥{{ Number(budget).toFixed(0) }}</span>
      </div>
      <div class="meter" :class="{ over }">
        <i :style="{ width: percent + '%' }"></i>
      </div>
      <p class="note num" :class="{ over }">
        <template v-if="over">已超支 ¥{{ Math.abs(left).toFixed(2) }}，留意支出节奏</template>
        <template v-else>剩余 ¥{{ left.toFixed(2) }}，进度 {{ percent.toFixed(0) }}%</template>
      </p>
    </template>
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
.top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}
.used {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text);
}
.budget {
  font-size: 0.82rem;
  color: var(--text-3);
}
.meter {
  margin-top: 12px;
  height: 8px;
  border-radius: var(--r-pill);
  background: var(--track);
  overflow: hidden;
}
.meter i {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--accent);
  transition: width 400ms var(--ease-out-quart), background 300ms ease;
}
.meter.over i {
  background: var(--heat);
}
.note {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--text-3);
}
.note.over {
  color: var(--heat);
  font-weight: 600;
}
.editor {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
