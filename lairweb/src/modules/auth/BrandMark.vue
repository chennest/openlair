<script setup lang="ts">
// 品牌标记：渐变 L 方块（登录/注册页等品牌场景复用）
withDefaults(defineProps<{ size?: number }>(), { size: 48 })
</script>

<template>
  <span
    class="brand-mark"
    :style="{
      width: size + 'px',
      height: size + 'px',
      borderRadius: Math.round(size * 0.3) + 'px',
      fontSize: Math.round(size * 0.42) + 'px',
    }"
  >L</span>
</template>

<style scoped>
.brand-mark {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  background: var(--grad-blue);
  color: #fff;
  font-weight: 800;
  /* var(--grad-blue) 是 background-image：必须 background 简写，写 background-color 会失效变透明 */
  box-shadow: var(--sh-cta);
}
</style>
