<script setup lang="ts">
// 记一笔弹窗：基于 BaseModal，表单状态由父组件传入
import { ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import { CATEGORIES, type CreateTransactionInput } from './api'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: CreateTransactionInput): void
}>()

const saving = ref(false)
const today = () => {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const form = ref<CreateTransactionInput>({ type: '支出', category: '餐饮', amount: 0, date: today(), note: '' })

// 每次打开时重置表单
watch(
  () => props.open,
  (open) => {
    if (open) form.value = { type: '支出', category: '餐饮', amount: 0, date: today(), note: '' }
  },
)

function pickCategory(name: string) {
  form.value.category = name
}

function submit() {
  const amount = Number(form.value.amount)
  if (!amount || amount <= 0) return
  saving.value = true
  emit('submit', { ...form.value, amount, date: form.value.date || undefined })
}
</script>

<template>
  <BaseModal v-if="open" title="记一笔" @close="emit('close')">
    <!-- 类型切换 -->
    <div class="type-switch">
      <button class="type-btn" :class="{ on: form.type === '支出' }" @click="form.type = '支出'">支出</button>
      <button class="type-btn income" :class="{ on: form.type === '收入' }" @click="form.type = '收入'">收入</button>
    </div>

    <!-- 金额 -->
    <label class="field-label">金额</label>
    <div class="amount-box">
      <span class="yuan">¥</span>
      <input
        v-model.number="form.amount"
        type="number"
        step="0.01"
        min="0.01"
        placeholder="0.00"
        autofocus
        @keyup.enter="submit"
      />
    </div>

    <!-- 分类 -->
    <label class="field-label">分类</label>
    <div class="cat-grid">
      <button
        v-for="c in CATEGORIES"
        :key="c"
        class="cat-btn"
        :class="{ on: form.category === c }"
        @click="pickCategory(c)"
      >{{ c }}</button>
    </div>

    <!-- 日期 + 备注 -->
    <div class="row2">
      <div>
        <label class="field-label">日期</label>
        <input v-model="form.date" type="date" class="input" />
      </div>
      <div>
        <label class="field-label">备注</label>
        <input v-model="form.note" type="text" placeholder="可选" class="input" @keyup.enter="submit" />
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" :disabled="saving || !form.amount || Number(form.amount) <= 0" @click="submit">
        {{ saving ? '保存中…' : '保存这笔' }}
      </button>
    </div>
  </BaseModal>
</template>

<style scoped>
.type-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 5px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
}
.type-btn {
  padding: 11px;
  border: 0;
  border-radius: 10px;
  color: rgba(242, 234, 223, 0.55);
  background: transparent;
  font-weight: 800;
  cursor: pointer;
  transition: all 160ms ease;
}
.type-btn.on {
  color: #14120f;
  background: #ffac8b;
}
.type-btn.income.on {
  color: #0e1f16;
  background: #8ee6a5;
}
.field-label {
  display: block;
  margin: 18px 0 8px;
  color: rgba(242, 234, 223, 0.55);
  font-size: 0.74rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.amount-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px;
  border: 1px solid rgba(246, 211, 122, 0.35);
  border-radius: 16px;
  background: rgba(246, 211, 122, 0.08);
}
.amount-box .yuan {
  color: #f6d37a;
  font-size: 1.3rem;
  font-weight: 800;
}
.amount-box input {
  flex: 1;
  min-width: 0;
  padding: 12px 0;
  border: 0;
  outline: none;
  color: #f6d37a;
  background: transparent;
  font-size: 2rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.amount-box input::placeholder {
  color: rgba(246, 211, 122, 0.35);
}
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.cat-btn {
  padding: 10px 6px;
  border: 1px solid rgba(242, 234, 223, 0.12);
  border-radius: 12px;
  color: rgba(242, 234, 223, 0.7);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 140ms ease;
}
.cat-btn:hover {
  border-color: rgba(246, 211, 122, 0.5);
}
.cat-btn.on {
  border-color: #f6d37a;
  color: #14120f;
  background: #f6d37a;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.input {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 12px;
  outline: none;
  color: #f2eadf;
  background: rgba(255, 255, 255, 0.06);
  font: inherit;
}
.input:focus {
  border-color: rgba(246, 211, 122, 0.7);
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
.btn-ghost {
  padding: 12px 18px;
  border: 1px solid rgba(242, 234, 223, 0.16);
  border-radius: 12px;
  color: rgba(242, 234, 223, 0.7);
  background: transparent;
  font-weight: 800;
  cursor: pointer;
}
.btn-ghost:hover {
  color: #f2eadf;
}
.btn-primary {
  min-width: 130px;
  padding: 12px 18px;
  border: 0;
  border-radius: 12px;
  color: #14120f;
  background: #f6d37a;
  font-weight: 900;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
@media (max-width: 640px) {
  .cat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .row2 {
    grid-template-columns: 1fr;
  }
}
</style>
