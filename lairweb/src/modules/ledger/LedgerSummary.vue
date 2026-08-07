<script setup lang="ts">
// 收支摘要：单行紧凑横条（唯一彩色时刻，wallet.html 模式压缩版）
// 布局：左「本月结余」大字 + 右「收入/支出」meta + 操作 slot
import type { LedgerSummary } from './api'

defineProps<{ summary: LedgerSummary }>()
</script>

<template>
  <section class="hero" aria-label="收支摘要">
    <div class="orb o1"></div>
    <div class="orb o2"></div>
    <div class="hero-in">
      <div class="left">
        <span class="lbl">本月结余</span>
        <div class="amt">¥{{ Number(summary.balance).toFixed(2) }}</div>
      </div>
      <div class="right">
        <div class="meta">
          <span class="num">收入 ¥{{ Number(summary.income).toFixed(2) }}</span>
          <span class="dot" aria-hidden="true"></span>
          <span class="num">支出 ¥{{ Number(summary.expense).toFixed(2) }}</span>
        </div>
        <slot name="action" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  border-radius: var(--r-hero);
  padding: 16px 22px;
  background: var(--grad-cta);
  box-shadow: var(--sh-cta);
}
.orb {
  position: absolute;
  border-radius: 50%;
}
.o1 {
  width: 200px;
  height: 200px;
  background: rgba(255, 255, 255, 0.18);
  filter: blur(46px);
  top: -80px;
  right: -30px;
}
.o2 {
  width: 160px;
  height: 160px;
  background: rgba(120, 80, 255, 0.5);
  filter: blur(50px);
  bottom: -80px;
  left: 12%;
}
.hero-in {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.left {
  display: flex;
  align-items: baseline;
  gap: 14px;
  min-width: 0;
}
.lbl {
  font-size: 13px;
  font-weight: 550;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
}
.amt {
  font-size: clamp(24px, 3vw, 32px);
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.right {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.82);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.45);
}
@media (max-width: 760px) {
  .hero-in {
    flex-wrap: wrap;
  }
  .right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
