<script setup lang="ts">
// 收支摘要：渐变结余 hero（唯一彩色时刻，wallet.html 模式）+ 收入/支出灰度卡
import type { LedgerSummary } from './api'

defineProps<{ summary: LedgerSummary }>()
</script>

<template>
  <section class="summary" aria-label="收支摘要">
    <div class="hero">
      <div class="orb o1"></div>
      <div class="orb o2"></div>
      <div class="hero-in">
        <span class="lbl">本月结余</span>
        <div class="amt">¥{{ Number(summary.balance).toFixed(2) }}</div>
        <div class="meta">
          <span class="num">收入 ¥{{ Number(summary.income).toFixed(2) }}</span>
          <span class="dot" aria-hidden="true"></span>
          <span class="num">支出 ¥{{ Number(summary.expense).toFixed(2) }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  border-radius: var(--r-hero);
  padding: clamp(24px, 3.6vw, 36px);
  background: var(--grad-cta);
  box-shadow: var(--sh-cta);
}
.orb {
  position: absolute;
  border-radius: 50%;
}
.o1 {
  width: 260px;
  height: 260px;
  background: rgba(255, 255, 255, 0.18);
  filter: blur(48px);
  top: -90px;
  right: -40px;
}
.o2 {
  width: 200px;
  height: 200px;
  background: rgba(120, 80, 255, 0.5);
  filter: blur(52px);
  bottom: -100px;
  left: 14%;
}
.hero-in {
  position: relative;
}
.lbl {
  font-size: 13px;
  font-weight: 550;
  color: rgba(255, 255, 255, 0.8);
}
.amt {
  margin-top: 6px;
  font-size: clamp(30px, 4vw, 40px);
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.82);
  font-variant-numeric: tabular-nums;
}
.dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.45);
}
</style>
