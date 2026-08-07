<script setup lang="ts">
// 预算卡：本月预算 + 已用 + 剩余 + meter（灰轨道 + accent 填充，超支转 heat）
// 内联编辑：点「调整」切换输入框
import { computed, ref } from 'vue'

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
      <button v-if="!editing" class="edit-btn" @click="startEdit">调整</button>
    </div>

    <div v-if="editing" class="editor">
      <input
        v-model="draft"
        type="number"
        min="0"
        step="100"
        class="input num"
        autofocus
        @keyup.enter="save"
        @keyup.esc="cancel"
      />
      <button class="save-btn" @click="save">保存</button>
      <button class="cancel-btn" @click="cancel">取消</button>
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
.edit-btn {
  border: 0;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  background: transparent;
  padding: 4px 8px;
  border-radius: var(--r-pill);
}
.edit-btn:hover {
  background: rgba(0, 113, 227, 0.06);
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
.input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  padding: 9px 12px;
  font-size: 1rem;
  color: var(--text);
  background: var(--surface);
  outline: none;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}
.save-btn,
.cancel-btn {
  border: 0;
  border-radius: var(--r-pill);
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.save-btn {
  color: #fff;
  background: var(--accent);
}
.cancel-btn {
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.05);
}
</style>
