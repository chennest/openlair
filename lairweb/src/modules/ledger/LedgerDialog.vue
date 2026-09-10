<script setup lang="ts">
// 记一笔弹窗：基于 BaseModal；分类列表随类型切换（支出/收入分类表）。
// 内含轻量「管理分类」视图（同一弹窗内切换，不叠层）：增删改本人自定义分类，
// 系统预置只读；删除被 409 拒绝（挂有流水）时在视图内展示原因。
import { ref, watch, computed } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Pencil, Trash2, Plus, ChevronLeft } from '@lucide/vue'
import { ApiError } from '../../api/request'
import { categoryApi } from './api'
import type { Category, CreateTransactionInput, Transaction } from './api'

const props = defineProps<{
  open: boolean
  categories: Category[]
  /** 传入 = 编辑该条流水；不传 = 记一笔 */
  transaction?: Transaction | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: CreateTransactionInput): void
  (e: 'update', payload: { id: number; patch: CreateTransactionInput }): void
  (e: 'refresh-categories'): void
}>()

/** 编辑态：标题/按钮文案随之切换 */
const isEdit = computed(() => !!props.transaction)

/** 弹窗内视图：记账表单 / 分类管理 */
const view = ref<'form' | 'manage'>('form')
const manageBusy = ref(false)
const manageError = ref('')
const newCatName = ref('')
const editingId = ref(0)
const editingName = ref('')

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

// 管理视图跟随表单当前类型
const manageList = computed(() =>
  props.categories.filter((c) => c.type === form.value.type).sort((a, b) => a.sortOrder - b.sortOrder),
)

// 每次打开时重置表单：编辑模式预填原流水，新建模式用默认值
watch(
  () => [props.open, props.transaction] as const,
  ([open, tx]) => {
    if (!open) return
    saving.value = false // 提交后父组件关闭弹窗，重新打开时复位保存态
    view.value = 'form'
    manageError.value = ''
    editingId.value = 0
    form.value = tx
      ? {
          type: tx.type,
          categoryId: tx.categoryId,
          amount: tx.amount,
          date: tx.date,
          note: tx.note ?? '',
        }
      : { type: '支出', categoryId: defaultCategoryId('支出'), amount: 0, date: today(), note: '' }
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
  const payload: CreateTransactionInput = {
    type: form.value.type,
    categoryId: form.value.categoryId,
    amount,
    date: form.value.date || undefined,
    note: form.value.note,
  }
  if (props.transaction) emit('update', { id: props.transaction.id, patch: payload })
  else emit('submit', payload)
}

// ---------- 分类管理 ----------

async function addCategory() {
  const name = newCatName.value.trim()
  if (!name || manageBusy.value) return
  manageBusy.value = true
  manageError.value = ''
  try {
    await categoryApi.create({ name, type: form.value.type })
    newCatName.value = ''
    emit('refresh-categories')
  } catch (e) {
    manageError.value = e instanceof ApiError ? e.message : '创建失败，请重试'
  } finally {
    manageBusy.value = false
  }
}

async function saveRename(c: Category) {
  const name = editingName.value.trim()
  if (!name || manageBusy.value) return
  manageBusy.value = true
  manageError.value = ''
  try {
    await categoryApi.rename(c.id, name)
    editingId.value = 0
    emit('refresh-categories')
  } catch (e) {
    manageError.value = e instanceof ApiError ? e.message : '修改失败，请重试'
  } finally {
    manageBusy.value = false
  }
}

async function deleteCategory(c: Category) {
  if (manageBusy.value) return
  manageBusy.value = true
  manageError.value = ''
  try {
    await categoryApi.remove(c.id)
    if (form.value.categoryId === c.id) form.value.categoryId = defaultCategoryId(form.value.type)
    emit('refresh-categories')
  } catch (e) {
    manageError.value = e instanceof ApiError ? e.message : '删除失败，请重试'
  } finally {
    manageBusy.value = false
  }
}
</script>

<template>
  <BaseModal v-if="open" :title="view === 'manage' ? '管理分类' : isEdit ? '编辑流水' : '记一笔'" @close="emit('close')">
    <!-- ═══ 分类管理视图 ═══ -->
    <template v-if="view === 'manage'">
      <button
        class="inline-flex items-center gap-1 text-[0.85rem] font-semibold text-[var(--text-3)] hover:text-[var(--text)] cursor-pointer bg-transparent border-none p-0"
        @click="view = 'form'"
      >
        <ChevronLeft class="size-4" />返回记账
      </button>

      <p class="mt-1 text-[0.78rem] leading-5 text-[var(--text-3)]">
        系统预置分类只读；自己创建的（标「我的」）可改名/删除。共享账本里所有成员的自定义分类通用。
      </p>

      <p v-if="manageError" class="mt-2 rounded-[var(--r-thumb)] bg-[rgba(255,59,48,0.08)] px-3 py-2 text-[0.8rem] text-[#ff3b30]">
        {{ manageError }}
      </p>

      <!-- 类型切换（与表单共用 form.type，回来时类型不跳） -->
      <Tabs v-model="form.type" class="type-tabs mt-3">
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

      <div class="mt-3 max-h-[300px] overflow-y-auto">
        <div v-for="c in manageList" :key="c.id" class="flex items-center gap-2 rounded-[var(--r-thumb)] px-2 py-[7px] hover:bg-[var(--hover)]">
          <template v-if="editingId === c.id">
            <Input
              v-model="editingName"
              class="h-8 flex-1 border-[var(--hairline)]! bg-white px-2 py-1 text-[0.88rem] shadow-none!"
              @keyup.enter="saveRename(c)"
            />
            <Button size="sm" class="h-8 rounded-full! px-3 text-[0.8rem]" :disabled="manageBusy" @click="saveRename(c)">保存</Button>
            <Button size="sm" variant="outline" class="h-8 rounded-full! px-3 text-[0.8rem] bg-white" @click="editingId = 0">取消</Button>
          </template>
          <template v-else>
            <span class="flex-1 truncate text-[0.92rem]">{{ c.name }}</span>
            <span
              v-if="c.userId === null"
              class="flex-none rounded-full bg-[rgba(0,0,0,0.05)] px-2 py-[2px] text-[0.68rem] font-semibold text-[var(--text-3)]"
            >系统</span>
            <span
              v-else
              class="flex-none rounded-full bg-[rgba(0,113,227,0.1)] px-2 py-[2px] text-[0.68rem] font-semibold text-[var(--accent)]"
            >我的</span>
            <template v-if="c.userId !== null">
              <Button
                variant="ghost" size="icon-sm"
                class="text-[var(--text-3)] hover:text-[var(--accent)]! hover:bg-transparent"
                aria-label="改名"
                @click="editingId = c.id; editingName = c.name"
              ><Pencil class="size-3.5" /></Button>
              <Button
                variant="ghost" size="icon-sm"
                class="text-[var(--text-3)] hover:text-[var(--heat)]! hover:bg-transparent"
                aria-label="删除分类"
                @click="deleteCategory(c)"
              ><Trash2 class="size-3.5" /></Button>
            </template>
            <span v-else class="w-[64px] flex-none" />
          </template>
        </div>
      </div>

      <!-- 新增行 -->
      <div class="mt-2 flex items-center gap-2 border-t border-[var(--hairline)] pt-3">
        <Input
          v-model="newCatName"
          class="h-10 flex-1 border-[var(--hairline)]! bg-white px-3 text-[0.9rem] shadow-none!"
          placeholder="新分类名称（20 字内）"
          maxlength="20"
          @keyup.enter="addCategory"
        />
        <Button class="h-10 rounded-full! px-4 text-[0.85rem] font-semibold" :disabled="manageBusy || !newCatName.trim()" @click="addCategory">
          <Plus class="size-4" />添加{{ form.type }}分类
        </Button>
      </div>
    </template>

    <!-- ═══ 记账表单视图 ═══ -->
    <template v-else>
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

      <!-- 分类（随类型切换；右侧入口进管理视图） -->
      <div class="mt-[18px] mb-2 flex items-center justify-between">
        <Label class="text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">分类</Label>
        <button
          class="text-[0.74rem] font-semibold text-[var(--accent)] hover:underline cursor-pointer bg-transparent border-none p-0"
          @click="view = 'manage'"
        >管理分类</button>
      </div>
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
          {{ saving ? '保存中…' : isEdit ? '保存修改' : '保存这笔' }}
        </Button>
      </div>
    </template>
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
