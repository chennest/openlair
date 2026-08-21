<script setup lang="ts">
// 输入邀请码加入共享账本：8 位码，自动大写 + 分段展示
import { computed, ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const props = defineProps<{
  open: boolean
  submitting: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'join', code: string): void
}>()

const code = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) code.value = ''
  },
)

const formatted = computed(() => (code.value.length > 4 ? `${code.value.slice(0, 4)}-${code.value.slice(4)}` : code.value))
const ready = computed(() => code.value.length === 8 && !props.submitting)

function onUpdate(value: string | number | undefined) {
  const raw = String(value ?? '')
  code.value = raw.toUpperCase().replace(/[^0-9A-Z]/g, '').slice(0, 8)
}

function submit() {
  if (!ready.value) return
  emit('join', code.value)
}
</script>

<template>
  <BaseModal v-if="open" title="加入共享账本" @close="emit('close')">
    <div class="join">
      <p class="desc">输入好友分享的邀请码，即可加入对方的共享账本一起记账。</p>

      <Input
        :model-value="formatted"
        inputmode="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="例如 KD7F-2GQW"
        maxlength="9"
        class="code-input"
        @update:model-value="onUpdate"
        @keyup.enter="submit"
      />

      <p v-if="error" class="err">{{ error }}</p>

      <div class="foot">
        <Button variant="outline" class="btn-ghost" @click="emit('close')">取消</Button>
        <Button class="btn-primary" :disabled="!ready" @click="submit">
          {{ submitting ? '加入中…' : '加入' }}
        </Button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.join {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.desc {
  margin: 0;
  font-size: 0.86rem;
  color: var(--text-2);
  line-height: 1.55;
}
.code-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  padding: 14px 16px;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-align: center;
  color: var(--text);
  background: var(--bg);
  outline: none;
  font-variant-numeric: tabular-nums;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.code-input::placeholder {
  font-weight: 500;
  letter-spacing: 0.02em;
  font-size: 0.95rem;
  color: var(--text-4);
}
.code-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}
.err {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--heat);
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--r-pill);
  color: var(--text);
  background: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: background 160ms ease;
}
.btn-ghost:hover {
  background: var(--hover);
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 22px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--accent);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 160ms ease;
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-primary:not(:disabled):hover {
  opacity: 0.88;
}
</style>
