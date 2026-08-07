<script setup lang="ts">
// 通用标签：variant 决定配色（token 化，来源 .agents/skills/apple-design-skill/components.md §6）
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
  padding: 3px 10px;
  border-radius: var(--r-pill);
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}
.gold {
  color: #fff;
  background: var(--accent);
}
.green {
  color: #0a5a2c;
  background: rgba(48, 209, 88, 0.16);
}
.gray {
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.05);
}
.red {
  color: var(--heat);
  background: var(--heat-bg);
}
</style>
