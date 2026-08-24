<script setup lang="ts">
// 创建 API Key 弹窗：两态（form 输入名称 → reveal 展示明文）
// 基于 BaseModal；父组件控制 open，关闭后明文即丢弃（仅当时可复制）
import { ref, watch } from 'vue'
import { Copy, KeyRound } from '@lucide/vue'
import BaseModal from '../../components/BaseModal.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const props = defineProps<{
  open: boolean
  /** 创建成功后待展示的明文（null = 还在 form 态） */
  pendingKey: string | null
  /** 提交进行中（父组件控制） */
  saving: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', name: string): void
}>()

const name = ref('')
const copied = ref(false)
const formError = ref('')

// 每次打开重置状态（规范：打开时 watch(props.open) 重置表单）
watch(
  () => props.open,
  (open) => {
    if (open) {
      name.value = ''
      copied.value = false
      formError.value = ''
    }
  },
)

function submit() {
  const n = name.value.trim()
  if (!n) {
    formError.value = '请填写名称'
    return
  }
  if (n.length > 30) {
    formError.value = '名称需为 1-30 个字符'
    return
  }
  formError.value = ''
  if (!props.saving) emit('submit', n)
}

async function copy() {
  if (!props.pendingKey) return
  try {
    await navigator.clipboard.writeText(props.pendingKey)
    copied.value = true
  } catch {
    // 剪贴板权限被拒时静默，用户仍可手动选中复制
  }
}

function close() {
  if (props.saving) return
  emit('close')
}
</script>

<template>
  <BaseModal v-if="open" :title="pendingKey ? 'API Key 已创建' : '创建 API Key'" @close="close">
    <!-- form 态：输入名称 -->
    <template v-if="!pendingKey">
      <Label class="mb-2 block text-[var(--text-3)] text-[0.74rem] font-semibold tracking-[0.04em]">名称</Label>
      <div class="name-box">
        <KeyRound class="name-icon" />
        <Input
          v-model="name"
          placeholder="如：我的 MCP 客户端"
          maxlength="30"
          class="h-11 flex-1 min-w-0 bg-transparent border-none shadow-none! pl-9"
          @keyup.enter="submit"
        />
      </div>
      <p class="form-error" v-if="formError">{{ formError }}</p>

      <div class="modal-foot">
        <Button variant="outline" class="h-11 px-[19px] rounded-full! font-semibold text-[13px] cursor-pointer" @click="close">
          取消
        </Button>
        <Button class="h-11 min-w-[130px] px-[18px] rounded-full! font-semibold text-[13px]" :disabled="saving" @click="submit">
          {{ saving ? '创建中…' : '创建' }}
        </Button>
      </div>
    </template>

    <!-- reveal 态：明文只展示一次 -->
    <template v-else>
      <p class="reveal-hint">请立即保存，关闭后无法再次查看明文。</p>
      <div class="key-plain">
        <code :class="{ 'is-copied': copied }">{{ pendingKey }}</code>
        <Button size="sm" variant="outline" class="copy-btn shrink-0" @click="copy">
          <Copy class="size-3.5" />
          {{ copied ? '已复制' : '复制' }}
        </Button>
      </div>
      <p class="reveal-prefix">前缀 {{ pendingKey.slice(0, 12) }}… 可在列表中识别此 Key</p>

      <div class="modal-foot">
        <Button class="h-11 min-w-[130px] px-[18px] rounded-full! font-semibold text-[13px]" @click="close">
          我已保存，关闭
        </Button>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.name-box {
  position: relative;
  display: flex;
  align-items: center;
  padding: 4px 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-card);
  background: var(--surface);
}
.name-icon {
  position: absolute;
  left: 13px;
  width: 16px;
  height: 16px;
  color: var(--text-3);
  pointer-events: none;
}
.form-error {
  margin: 8px 2px 0;
  color: var(--heat);
  font-size: 12.5px;
}

.reveal-hint {
  margin: 0 0 12px;
  color: var(--heat);
  font-size: 13px;
  font-weight: 600;
}
.key-plain {
  display: flex;
  align-items: center;
  gap: 10px;
}
.key-plain code {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding: 11px 13px;
  border-radius: var(--r-thumb);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  white-space: nowrap;
  transition: color 250ms;
}
.key-plain code.is-copied {
  color: var(--live);
}
.copy-btn {
  flex: 0 0 auto;
}
.reveal-prefix {
  margin: 10px 2px 0;
  color: var(--text-3);
  font-size: 12.5px;
}

.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
</style>
