<script setup lang="ts">
// 新建账本弹窗：个人账本或共享账本
import { ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const props = defineProps<{ open: boolean }>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', input: { name: string; type: 'personal' | 'shared' }): void
}>()

const type = ref<'personal' | 'shared'>('shared')
const name = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      type.value = 'shared'
      name.value = ''
    }
  },
)

function submit() {
  if (!name.value.trim()) return
  emit('create', { name: name.value.trim(), type: type.value })
}
</script>

<template>
  <BaseModal v-if="open" title="新建账本" @close="emit('close')">
    <!-- 类型 -->
    <Label class="mt-4 mb-2 text-[12px] font-semibold text-[var(--text-3)]">账本类型</Label>
    <div class="types">
      <Button
        variant="outline"
        class="flex-col items-start justify-start gap-1 h-auto px-[14px] py-[14px] rounded-[var(--r-card)]! text-foreground bg-white text-left cursor-pointer transition-colors hover:border-[rgba(0,113,227,0.4)] hover:bg-white"
        :class="type === 'shared' ? 'border-primary bg-primary/6' : ''"
        @click="type = 'shared'"
      >
        <span class="t-name">共享账本</span>
        <span class="t-desc">多人一起记账（家庭、旅行、合租…）</span>
      </Button>
      <Button
        variant="outline"
        class="flex-col items-start justify-start gap-1 h-auto px-[14px] py-[14px] rounded-[var(--r-card)]! text-foreground bg-white text-left cursor-pointer transition-colors hover:border-[rgba(0,113,227,0.4)] hover:bg-white"
        :class="type === 'personal' ? 'border-primary bg-primary/6' : ''"
        @click="type = 'personal'"
      >
        <span class="t-name">个人账本</span>
        <span class="t-desc">仅自己可见的流水</span>
      </Button>
    </div>

    <Label class="mt-4 mb-2 text-[12px] font-semibold text-[var(--text-3)]">账本名称</Label>
    <Input
      v-model="name"
      class="h-[42px] px-3 py-[11px] border-[var(--hairline)]! rounded-[var(--r-thumb)]! text-foreground bg-white shadow-none! text-[0.95rem] md:text-[0.95rem]"
      placeholder="如：家庭共享账本 / 大理旅行"
      maxlength="20"
      @keyup.enter="submit"
    />

    <div class="foot">
      <Button variant="outline" class="h-11 pl-[19px] pr-[19px] rounded-full! text-foreground bg-white/80 font-semibold cursor-pointer" @click="emit('close')">取消</Button>
      <Button class="min-w-[100px] h-11 pl-[18px] pr-[18px] rounded-full! font-semibold disabled:opacity-[0.45]" :disabled="!name.trim()" @click="submit">创建</Button>
    </div>
  </BaseModal>
</template>

<style scoped>
.types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.t-name {
  font-size: 0.95rem;
  font-weight: 700;
}
.t-desc {
  font-size: 12px;
  color: var(--text-3);
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
@media (max-width: 640px) {
  .types {
    grid-template-columns: 1fr;
  }
}
</style>
