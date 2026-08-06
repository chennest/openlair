<script setup lang="ts">
// 通用标签：variant 决定配色
withDefaults(
  defineProps<{
    variant?: 'gold' | 'green' | 'gray' | 'red'
  }>(),
  { variant: 'gray' },
)
</script>

<template>
  <span class="tag" :class="variant"><slot /></span>
</template>

<style scoped>
.tag {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
}
.gold {
  color: #14120f;
  background: #f6d37a;
}
.green {
  color: #0e1f16;
  background: #8ee6a5;
}
.gray {
  color: rgba(242, 234, 223, 0.7);
  background: rgba(255, 255, 255, 0.08);
}
.red {
  color: #ffd9c9;
  background: rgba(204, 93, 43, 0.28);
}
</style>
