<script setup lang="ts">
// 导入词书弹窗：Anki 导出文本、ECDICT CSV、简单行文本
import { computed, ref, watch } from 'vue'
import { FileUp, Loader2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
const source = ref<'paste' | 'file'>('paste')
const activeText = computed(() => (source.value === 'file' ? fileText.value : pastedText.value))

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
    <div v-if="result" class="result">
      <p class="result-title">导入成功</p>
      <ul class="result-list">
        <li>词书：<b>{{ result.book.emoji }} {{ result.book.name }}</b></li>
        <li>单词：<b>{{ result.imported }}</b> 个（新词条 {{ result.newWords }} 个）</li>
        <li>识别格式：{{ result.format === 'anki' ? 'Anki 导出文本' : result.format === 'ecdict' ? 'ECDICT CSV' : '简单行格式' }}</li>
        <li>可见范围：{{ result.book.ownerId === null ? '系统级（所有人可见）' : '仅本人可见' }}</li>
      </ul>
      <div class="foot"><Button class="flex-1" @click="emit('close')">完成</Button></div>
    </div>

    <form v-else class="form" @submit.prevent="submit">
      <div class="field">
        <Label for="import-name">词书名称</Label>
        <Input id="import-name" v-model="name" placeholder="可留空：自动读取 Anki 的 #deck 名" maxlength="100" />
      </div>

      <div class="field">
        <Label>可见级别</Label>
        <Tabs v-model="scope" class="choice-tabs">
          <TabsList class="segmented-list">
            <TabsTrigger value="user" class="segment">我的词书</TabsTrigger>
            <TabsTrigger value="system" class="segment">系统词书</TabsTrigger>
          </TabsList>
        </Tabs>
        <p class="hint">{{ scope === 'system' ? '所有人可见，仅首位用户可导入和删除' : '仅本人可见，可随时删除' }}</p>
      </div>

      <div class="field content-field">
        <Label>词书内容</Label>
        <Tabs v-model="source" class="choice-tabs">
          <TabsList class="segmented-list" aria-label="选择内容来源">
            <TabsTrigger value="paste" class="segment">粘贴文本</TabsTrigger>
            <TabsTrigger value="file" class="segment">上传文件</TabsTrigger>
          </TabsList>
        </Tabs>

        <Textarea
          v-if="source === 'paste'"
          v-model="pastedText"
          class="import-textarea"
          placeholder="每行一个单词，可选释义：&#10;cancel,vt. 取消；撤销&#10;ubiquitous 无处不在&#10;&#10;支持 Anki 导出文本、ECDICT CSV 与简单行格式"
        />
        <div v-else class="upload-area">
          <label class="file-btn">
            <FileUp class="size-5" />
            <span>{{ fileName || '选择 .txt / .csv / .tsv 文件' }}</span>
            <input type="file" accept=".txt,.csv,.tsv,text/plain,text/csv" class="hidden" @change="onPickFile" />
          </label>
          <p class="hint">文件内容支持 Anki 导出文本、ECDICT CSV 与简单行格式</p>
        </div>
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
:deep(.modal) {
  width: min(560px, 100%);
}
.form,
.result {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.content-field {
  gap: 10px;
}
.hint {
  margin: 0;
  color: var(--text-3);
  font-size: 0.78rem;
  line-height: 1.45;
}
.error {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--r-thumb);
  background: rgba(255, 59, 48, 0.08);
  color: var(--destructive);
  font-size: 0.84rem;
}
.choice-tabs,
.segmented-list {
  width: 100%;
}
.segmented-list {
  height: 40px;
  padding: 3px;
  border-radius: var(--r-pill);
  background: rgba(0, 0, 0, 0.05);
}
.segment {
  flex: 1;
  height: 34px;
  border-radius: var(--r-pill);
  color: var(--text-2);
  font-size: 0.84rem;
}
.segment[data-state='active'] {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}
.file-btn:focus-within {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.import-textarea {
  width: 100%;
  min-height: 190px;
  resize: vertical;
  line-height: 1.55;
}
.upload-area {
  display: flex;
  min-height: 190px;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 10px;
  padding: 18px;
  border: 1px dashed var(--hairline);
  border-radius: var(--r-sheet);
  background: var(--hover);
}
.file-btn {
  display: flex;
  min-height: 112px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: var(--r-thumb);
  color: var(--text-2);
  font-size: 0.9rem;
  cursor: pointer;
}
.file-btn:hover {
  background: rgba(var(--accent-rgb), 0.05);
  color: var(--accent);
}
.foot {
  display: flex;
  gap: 10px;
  margin-top: 2px;
}
.result-title {
  margin: 0;
  text-align: center;
  font-size: 1.05rem;
  font-weight: 700;
}
.result-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 14px 16px;
  list-style: none;
  border-radius: var(--r-thumb);
  background: var(--bg);
  color: var(--text-2);
  font-size: 0.88rem;
}
.result-list b {
  color: var(--text);
}
</style>
