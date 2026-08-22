<script setup lang="ts">
// 记一笔弹窗：基于 BaseModal；分类列表随类型切换（支出/收入分类表）
import { ref, watch, computed } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { Category, CreateTransactionInput } from './api'

const props = defineProps<{
  open: boolean
  categories: Category[]
}>()

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

const defaultCategoryId = (type: '支出' | '收入') => {
  const list = props.categories.filter((c) => c.type === type)
  return list.find((c) => c.isDefault)?.id ?? list[0]?.id ?? 0
}

const form = ref<{ type: '支出' | '收入'; categoryId: number; amount: number; date: string; note: string }>({
  type: '支出',
  categoryId: 0,
  amount: 0,
  date: today(),
  note: '',
})

// 当前类型对应的分类（数据源：分类表接口）
const categoryOptions = computed(() => props.categories.filter((c) => c.type === form.value.type))

// 每次打开时重置表单；类型切换时若分类不属于该类型则重置
watch(
  () => props.open,
  (open) => {
    if (open) {
      form.value = { type: '支出', categoryId: defaultCategoryId('支出'), amount: 0, date: today(), note: '' }
    }
  },
)

watch(
  () => form.value.type,
  (type) => {
    if (!categoryOptions.value.some((c) => c.id === form.value.categoryId)) {
      form.value.categoryId = defaultCategoryId(type)
    }
  },
)

function pickCategory(id: number) {
  form.value.categoryId = id
}

function submit() {
  const amount = Number(form.value.amount)
  if (!amount || amount <= 0 || !form.value.categoryId) return
  saving.value = true
  emit('submit', {
    type: form.value.type,
    categoryId: form.value.categoryId,
    amount,
    date: form.value.date || undefined,
    note: form.value.note,
  })
}
</script>

<template>
  <BaseModal v-if="open" title="记一笔" @close="emit('close')">
    <!-- 类型切换（Tabs 白胶囊 segmented） -->
    <Tabs v-model="form.type" class="type-tabs">
      <TabsList class="type-switch">
        <TabsTrigger
          value="支出"
          class="h-auto flex-none px-[11px] py-[11px] rounded-full! text-muted-foreground bg-transparent font-semibold data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-bold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
        >支出</TabsTrigger>
        <TabsTrigger
          value="收入"
          class="h-auto flex-none px-[11px] py-[11px] rounded-full! text-muted-foreground bg-transparent font-semibold data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:font-bold data-[state=active]:shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
        >收入</TabsTrigger>
      </TabsList>
    </Tabs>

    <!-- 金额 -->
    <Label class="mt-[18px] mb-2 text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">金额</Label>
    <div class="amount-box">
      <span class="yuan">¥</span>
      <Input
        v-model.number="form.amount"
        type="number"
        step="0.01"
        min="0.01"
        placeholder="0.00"
        autofocus
        class="flex-1 min-w-0 h-auto py-3 pl-0 pr-0 border-none text-[var(--text)] bg-transparent text-[2rem] md:text-[2rem] font-bold tabular-nums shadow-none! placeholder:text-[var(--text-4)]!"
        @keyup.enter="submit"
      />
    </div>

    <!-- 分类（随类型切换） -->
    <Label class="mt-[18px] mb-2 text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">分类</Label>
    <div class="cat-grid">
      <Button
        v-for="c in categoryOptions"
        :key="c.id"
        variant="outline"
        class="h-auto py-2.5 px-[6px] rounded-[var(--r-thumb)]! text-muted-foreground bg-white text-[0.88rem] font-semibold cursor-pointer transition-all hover:border-[rgba(0,113,227,0.4)] hover:text-muted-foreground"
        :class="form.categoryId === c.id ? 'border-primary text-white bg-primary hover:bg-primary hover:text-white hover:border-primary' : ''"
        @click="pickCategory(c.id)"
      >{{ c.name }}</Button>
    </div>

    <!-- 日期 + 备注 -->
    <div class="row2">
      <div>
        <Label class="mt-[18px] mb-2 text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">日期</Label>
        <Input v-model="form.date" type="date" class="h-[42px] px-3 py-[11px] border-[var(--hairline)]! rounded-[var(--r-thumb)]! text-foreground bg-white shadow-none!" />
      </div>
      <div>
        <Label class="mt-[18px] mb-2 text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">备注</Label>
        <Input v-model="form.note" type="text" placeholder="可选" class="h-[42px] px-3 py-[11px] border-[var(--hairline)]! rounded-[var(--r-thumb)]! text-foreground bg-white shadow-none!" @keyup.enter="submit" />
      </div>
    </div>

    <div class="modal-foot">
      <Button variant="outline" class="h-11 pl-[19px] pr-[19px] rounded-full! text-foreground bg-white/80 font-semibold text-[13px] cursor-pointer" @click="emit('close')">取消</Button>
      <Button class="min-w-[130px] h-11 pl-[18px] pr-[18px] rounded-full! font-semibold text-[13px] hover:shadow-[var(--sh-cta)] disabled:opacity-[0.45]" :disabled="saving || !form.amount || Number(form.amount) <= 0 || !form.categoryId" @click="submit">
        {{ saving ? '保存中…' : '保存这笔' }}
      </Button>
    </div>
  </BaseModal>
</template>

<style scoped>
.type-tabs {
  width: 100%;
}
.type-switch {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  height: auto;
  padding: 4px;
  border-radius: var(--r-pill);
  background: rgba(0, 0, 0, 0.05);
}
.amount-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-card);
  background: rgba(0, 113, 227, 0.04);
}
.amount-box .yuan {
  color: var(--accent);
  font-size: 1.3rem;
  font-weight: 700;
}
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
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
