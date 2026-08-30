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
        class="py-[14px] pl-4 pr-4 border-[var(--hairline)]! rounded-[var(--r-thumb)]! text-[1.5rem] md:text-[1.5rem] font-bold tracking-[0.14em] text-center text-foreground bg-[var(--bg)]! tabular-nums shadow-none! placeholder:font-medium placeholder:tracking-[0.02em] placeholder:text-[0.95rem] placeholder:text-[var(--text-4)]!"
        @update:model-value="onUpdate"
        @keyup.enter="submit"
      />

      <p v-if="error" class="err">{{ error }}</p>

      <div class="foot">
        <Button variant="outline" class="h-[42px] pl-[18px] pr-[18px] rounded-full! text-foreground bg-white/80 font-semibold text-[13px] cursor-pointer" @click="emit('close')">取消</Button>
        <Button class="h-[42px] pl-[22px] pr-[22px] rounded-full! font-semibold text-[13px] hover:opacity-[0.88] disabled:opacity-[0.45]" :disabled="!ready" @click="submit">
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
</style>
