<script setup lang="ts">
// 通用弹窗：Teleport + 遮罩点击关闭 + 缩放动画 + 标题栏
defineProps<{
  title?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="true" class="modal-mask" @click.self="emit('close')">
        <div class="modal" role="dialog" aria-modal="true" :aria-label="title || '对话框'">
          <div v-if="title" class="modal-head">
            <h2>{{ title }}</h2>
            <button class="close-btn" aria-label="关闭" @click="emit('close')">✕</button>
          </div>
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(8, 7, 5, 0.66);
  backdrop-filter: blur(8px);
}
.modal {
  width: min(460px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 26px 26px 22px;
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 26px;
  background: rgba(28, 24, 18, 0.97);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.5);
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.modal-head h2 {
  margin: 0;
  font-size: 1.3rem;
  letter-spacing: -0.02em;
}
.close-btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(242, 234, 223, 0.14);
  border-radius: 999px;
  color: rgba(242, 234, 223, 0.6);
  background: transparent;
  cursor: pointer;
}
.close-btn:hover {
  color: #ffac8b;
  border-color: rgba(255, 172, 139, 0.4);
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 220ms ease;
}
.modal-enter-active .modal,
.modal-leave-active .modal {
  transition: transform 220ms ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: translateY(14px) scale(0.97);
}
</style>
