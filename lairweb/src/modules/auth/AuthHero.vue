<script setup lang="ts">
// 登录/注册页左侧品牌面板：SVG 山水场景 + 品牌行 + 主张 + 三个特性（纯展示组件）
// 设计稿：雾蓝远山 + 玻璃星球；颜色属 hero 插画范畴（--grad-blue 同族的雾蓝阶），不进 UI token
import { Zap, ShieldCheck, Blocks } from '@lucide/vue'
import BrandMark from './BrandMark.vue'

const feats = [
  { icon: Zap, title: '智能高效', desc: 'AI 助力，提升效率' },
  { icon: ShieldCheck, title: '安全可靠', desc: '数据加密，隐私保护' },
  { icon: Blocks, title: '开放生态', desc: '连接更多 AI 能力' },
]
</script>

<template>
  <div class="hero">
    <!-- 场景插画：雾蓝天空 + 玻璃星球 + 三层远山 + 白雾 -->
    <svg
      class="scene"
      viewBox="0 0 640 800"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="auth-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#f0f6fd" />
          <stop offset="1" stop-color="#d8e8f8" />
        </linearGradient>
        <radialGradient id="auth-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stop-color="#ffffff" stop-opacity="0.9" />
          <stop offset="1" stop-color="#ffffff" stop-opacity="0" />
        </radialGradient>
        <linearGradient id="auth-sphere" x1="0" y1="0" x2="0.6" y2="1">
          <stop offset="0" stop-color="#ffffff" stop-opacity="0.95" />
          <stop offset="1" stop-color="#cfe2f6" stop-opacity="0.9" />
        </linearGradient>
        <filter id="auth-mist" x="-40%" y="-120%" width="180%" height="340%">
          <feGaussianBlur stdDeviation="20" />
        </filter>
      </defs>

      <rect width="640" height="800" fill="url(#auth-sky)" />
      <circle cx="452" cy="238" r="180" fill="url(#auth-glow)" />

      <!-- 玻璃星球（球体 + 斜环 + 高光） -->
      <g transform="translate(452 238)">
        <circle r="72" fill="url(#auth-sphere)" />
        <circle r="72" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5" />
        <ellipse
          rx="102" ry="26" fill="none" stroke="#ffffff"
          stroke-opacity="0.65" stroke-width="3"
          transform="rotate(-18)" 
        />
        <ellipse cx="-26" cy="-28" rx="16" ry="10" fill="#ffffff" opacity="0.8" transform="rotate(-24 -26 -28)" />
      </g>

      <!-- 三层远山（远浅近深的大气透视，低伏不压主张区） -->
      <path
        d="M0 528 L96 452 L176 512 L266 438 L356 516 L436 456 L524 518 L640 448 L640 800 L0 800 Z"
        fill="#cdddf3" opacity="0.85"
      />
      <path
        d="M0 602 L112 530 L202 594 L312 514 L422 602 L522 534 L640 608 L640 800 L0 800 Z"
        fill="#b9d2ef"
      />
      <path
        d="M0 686 L142 614 L262 680 L382 602 L502 678 L640 614 L640 800 L0 800 Z"
        fill="#a6c5ea" opacity="0.9"
      />

      <!-- 白雾带 -->
      <ellipse cx="320" cy="664" rx="430" ry="92" fill="#ffffff" opacity="0.55" filter="url(#auth-mist)" />
      <ellipse cx="110" cy="722" rx="270" ry="72" fill="#ffffff" opacity="0.45" filter="url(#auth-mist)" />
      <ellipse cx="548" cy="600" rx="210" ry="62" fill="#ffffff" opacity="0.4" filter="url(#auth-mist)" />
    </svg>

    <div class="hero-body">
      <!-- 品牌行 -->
      <div class="brand">
        <BrandMark :size="48" />
        <div class="brand-col">
          <p class="brand-name">OpenLair</p>
          <p class="brand-sub">个人 AI 生活工作台</p>
        </div>
      </div>

      <!-- 主张 -->
      <div class="claim">
        <h1 class="claim-title">让 AI 走进你的工作与生活</h1>
        <p class="claim-sub">用 AI 提升效率，记录灵感，<br />打造属于你的智能工作台。</p>
      </div>

      <!-- 特性 -->
      <ul class="feats">
        <li v-for="f in feats" :key="f.title" class="feat">
          <span class="feat-chip"><component :is="f.icon" class="feat-icon" /></span>
          <span class="feat-col">
            <b class="feat-title">{{ f.title }}</b>
            <span class="feat-desc">{{ f.desc }}</span>
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: linear-gradient(180deg, #eef4fc, #d8e8f8);
}

.scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.hero-body {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: clamp(24px, 3.5vw, 36px);
}

/* 品牌行 */
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-col {
  min-width: 0;
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text);
}

.brand-sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-2);
}

/* 主张（垂直居中于品牌与特性之间） */
.claim {
  margin-top: auto;
  margin-bottom: auto;
}

.claim-title {
  font-size: clamp(22px, 2.4vw, 28px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.18;
  color: var(--text);
}

.claim-sub {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-2);
}

/* 特性（底部一行，窄幅自动换行） */
.feats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 18px;
  margin-top: auto;
  padding-top: 24px;
  list-style: none;
}

.feat {
  display: flex;
  align-items: center;
  gap: 10px;
}

.feat-chip {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: var(--sh-card);
}

.feat-icon {
  width: 18px;
  height: 18px;
  color: var(--accent);
}

.feat-col {
  display: flex;
  flex-direction: column;
}

.feat-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.feat-desc {
  margin-top: 1px;
  font-size: 11px;
  color: var(--text-3);
}
</style>
