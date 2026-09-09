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
  /* 用 flex 居中替代 grid place-items：grid 项在内容不足时会被拉伸出多余空白 */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.28);
}
.modal {
  width: min(460px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  /* 高度贴合内容，避免 flex 居中时容器被拉伸留白 */
  height: auto;
  padding: 26px 26px 22px;
  border-radius: var(--r-hero);
  /* 纯白表面 + 柔和双层阴影（规范：普通内容不用玻璃层）。
     此前 transition 结束态给 .modal 加了 backdrop-filter，与半透明遮罩
     叠加后透出深色模糊层，表现为弹窗上的异常灰底 —— 已移除。 */
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
/* materialize：遮罩淡入略快于表面；表面 opacity+scale 同路进出。
   弹窗表面为纯白实色，不加玻璃层（backdrop-filter 会透出深色遮罩形成灰底） */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 250ms ease;
}
.modal-enter-active .modal,
.modal-leave-active .modal {
  transition:
    opacity 400ms var(--ease-spring),
    transform 400ms var(--ease-spring);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal,
.modal-leave-to .modal {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}
.modal-enter-to .modal,
.modal-leave-from .modal {
  opacity: 1;
  transform: none;
}
@media (prefers-reduced-motion: reduce) {
  .modal-enter-active .modal,
  .modal-leave-active .modal {
    transition: opacity 200ms ease;
    transform: none !important;
  }
}
@media (prefers-reduced-transparency: reduce) {
  .modal {
    backdrop-filter: none;
  }
}
</style>
