<script setup lang="ts">
// 导入词书弹窗：粘贴文本 / 上传文件（txt/csv），支持 Anki 导出文本、ECDICT CSV、简单行格式
// API 调用由父组件（index.vue）完成，本组件只收集输入与展示结果（props 进 emit 出）
import { computed, ref, watch } from 'vue'
import { FileUp, Loader2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import BaseModal from '../../components/BaseModal.vue'
import type { ImportBooksResult, VocabImportScope } from './api'

const props = defineProps<{
  open: boolean
  importing: boolean
  result: ImportBooksResult | null
  error: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', input: { name: string; scope: VocabImportScope; lang: string; text: string }): void
}>()

const name = ref('')
const scope = ref<VocabImportScope>('user')
const pastedText = ref('')
const fileText = ref('')
const fileName = ref('')

const activeText = computed(() => (source.value === 'file' ? fileText.value : pastedText.value))
const source = ref<'paste' | 'file'>('paste')

function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  fileName.value = file.name
  const reader = new FileReader()
  reader.onload = () => (fileText.value = String(reader.result ?? ''))
  reader.readAsText(file)
}

function submit() {
  if (!activeText.value.trim() || props.importing) return
  emit('submit', { name: name.value.trim(), scope: scope.value, lang: 'en', text: activeText.value })
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      name.value = ''
      scope.value = 'user'
      pastedText.value = ''
      fileText.value = ''
      fileName.value = ''
      source.value = 'paste'
    }
  },
)
</script>

<template>
  <BaseModal v-if="open" title="导入词书" @close="emit('close')">
    <!-- 导入成功结果 -->
    <div v-if="result" class="result">
      <p class="result-title">导入成功 🎉</p>
      <ul class="result-list">
        <li>词书：<b>{{ result.book.emoji }} {{ result.book.name }}</b></li>
        <li>单词：<b>{{ result.imported }}</b> 个（新词条 {{ result.newWords }} 个）</li>
        <li>识别格式：{{ result.format === 'anki' ? 'Anki 导出文本' : result.format === 'ecdict' ? 'ECDICT CSV' : '简单行格式' }}</li>
        <li>可见范围：{{ result.book.ownerId === null ? '系统级（所有人可见）' : '仅本人可见' }}</li>
      </ul>
      <div class="foot">
        <Button class="flex-1" @click="emit('close')">完成</Button>
      </div>
    </div>

    <!-- 导入表单 -->
    <form v-else class="form" @submit.prevent="submit">
      <div class="field">
        <Label for="import-name">词书名称</Label>
        <Input id="import-name" v-model="name" placeholder="可留空：自动读取 Anki 的 #deck 名" maxlength="100" />
      </div>

      <div class="field">
        <Label>可见级别</Label>
        <Tabs v-model="scope">
          <TabsList class="w-full">
            <TabsTrigger value="user" class="flex-1">我的词书</TabsTrigger>
            <TabsTrigger value="system" class="flex-1">系统词书</TabsTrigger>
          </TabsList>
        </Tabs>
        <p class="hint">{{ scope === 'system' ? '所有人可见，仅站长（首位用户）可导入和删除' : '仅本人可见，可随时删除' }}</p>
      </div>

      <div class="field">
        <Label>词书内容</Label>
        <Tabs v-model="source">
          <TabsList class="w-full">
            <TabsTrigger value="paste" class="flex-1">粘贴文本</TabsTrigger>
            <TabsTrigger value="file" class="flex-1">上传文件</TabsTrigger>
          </TabsList>
          <TabsContent value="paste">
            <Textarea
              v-model="pastedText"
              class="min-h-[140px] font-mono text-[13px]"
              placeholder="每行一个单词，可选释义：&#10;cancel,vt. 取消；撤销&#10;ubiquitous 无处不在&#10;&#10;支持 Anki 导出文本（含 #separator/#deck 头）与 ECDICT CSV"
            />
          </TabsContent>
          <TabsContent value="file">
            <label class="file-btn">
              <FileUp class="size-4" />
              {{ fileName || '选择 .txt / .csv 文件' }}
              <input type="file" accept=".txt,.csv,.tsv,text/plain,text/csv" class="hidden" @change="onPickFile" />
            </label>
            <p class="hint">文件内容同样支持 Anki 导出文本、ECDICT CSV 与简单行格式</p>
          </TabsContent>
        </Tabs>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div class="foot">
        <Button type="button" variant="ghost" class="flex-1" :disabled="importing" @click="emit('close')">取消</Button>
        <Button type="submit" class="flex-1" :disabled="importing || !activeText.trim()">
          <Loader2 v-if="importing" class="size-4 animate-spin" />
          {{ importing ? '导入中…' : '导入' }}
        </Button>
      </div>
    </form>
  </BaseModal>
</template>

<style scoped>
.form,
.result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-3);
}
.error {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--r-thumb);
  background: rgba(255, 59, 48, 0.08);
  color: #ff3b30;
  font-size: 0.84rem;
}
.foot {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}
.file-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border: 1px dashed var(--hairline);
  border-radius: var(--r-thumb);
  color: var(--text-2);
  font-size: 0.86rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.file-btn:hover {
  border-color: var(--accent);
  background: rgba(0, 113, 227, 0.04);
}
.result-title {
  margin: 0;
  text-align: center;
  font-size: 1.05rem;
  font-weight: 700;
}
.result-list {
  margin: 0;
  padding: 14px 16px;
  list-style: none;
  background: rgba(0, 0, 0, 0.03);
  border-radius: var(--r-thumb);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.88rem;
  color: var(--text-2);
}
.result-list b {
  color: var(--text);
}
</style>
