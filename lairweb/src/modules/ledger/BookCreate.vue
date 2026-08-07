<script setup lang="ts">
// 新建账本弹窗：个人账本或共享账本
import { ref, watch } from 'vue'
import BaseModal from '../../components/BaseModal.vue'

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
    <label class="label">账本类型</label>
    <div class="types">
      <button class="type-btn" :class="{ on: type === 'shared' }" @click="type = 'shared'">
        <span class="t-name">共享账本</span>
        <span class="t-desc">多人一起记账（家庭、旅行、合租…）</span>
      </button>
      <button class="type-btn" :class="{ on: type === 'personal' }" @click="type = 'personal'">
        <span class="t-name">个人账本</span>
        <span class="t-desc">仅自己可见的流水</span>
      </button>
    </div>

    <label class="label">账本名称</label>
    <input
      v-model="name"
      class="input"
      placeholder="如：家庭共享账本 / 大理旅行"
      maxlength="20"
      @keyup.enter="submit"
    />

    <div class="foot">
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" :disabled="!name.trim()" @click="submit">创建</button>
    </div>
  </BaseModal>
</template>

<style scoped>
.label {
  display: block;
  margin: 16px 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
}
.types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.type-btn {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-card);
  background: var(--surface);
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease;
}
.type-btn:hover {
  border-color: rgba(0, 113, 227, 0.4);
}
.type-btn.on {
  border-color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
}
.t-name {
  font-size: 0.95rem;
  font-weight: 700;
}
.t-desc {
  font-size: 12px;
  color: var(--text-3);
}
.input {
  width: 100%;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  padding: 11px 12px;
  font-size: 0.95rem;
  color: var(--text);
  background: var(--surface);
  outline: none;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  height: 44px;
  padding: 0 19px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--r-pill);
  color: var(--text);
  background: rgba(255, 255, 255, 0.8);
  font-weight: 600;
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
  min-width: 100px;
  height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--accent);
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
@media (max-width: 640px) {
  .types {
    grid-template-columns: 1fr;
  }
}
</style>
