<script setup lang="ts">
// 通用弹窗：Teleport + 遮罩点击关闭 + materialize 动画 + 标题栏
// 材质规范：.agents/skills/apple-design-skill/motion.md（blur+scale+opacity 同时进场）
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
  background: rgba(0, 0, 0, 0.28);
}
.modal {
  width: min(460px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 26px 26px 22px;
  border-radius: var(--r-hero);
  background: var(--surface);
  box-shadow: var(--sh-overlay);
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
  border: 0;
  border-radius: var(--r-pill);
  color: var(--text-3);
  background: rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease;
}
.close-btn:hover {
  color: var(--text);
  background: rgba(0, 0, 0, 0.08);
}
/* materialize：遮罩淡入略快于表面；表面 blur+scale+opacity 同路进出 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 250ms ease;
}
.modal-enter-active .modal,
.modal-leave-active .modal {
  transition:
    opacity 400ms var(--ease-spring),
    transform 400ms var(--ease-spring),
    backdrop-filter 400ms var(--ease-spring);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal,
.modal-leave-to .modal {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
  backdrop-filter: blur(0px);
}
.modal-enter-to .modal,
.modal-leave-from .modal {
  opacity: 1;
  transform: none;
  backdrop-filter: blur(20px) saturate(180%);
}
@media (prefers-reduced-motion: reduce) {
  .modal-enter-active .modal,
  .modal-leave-active .modal {
    transition: opacity 200ms ease;
    transform: none !important;
    backdrop-filter: none;
  }
}
@media (prefers-reduced-transparency: reduce) {
  .modal {
    backdrop-filter: none;
  }
}
</style>
