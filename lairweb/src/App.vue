<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const pageTitle = computed(() => (route.meta.title as string) || '总揽')

const navItems = [
  { path: '/', label: '总揽', icon: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
  { path: '/ledger', label: '记账', icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm1-13h-2v1.2A4 4 0 0 0 8.5 11h2a2 2 0 0 1 4 0h2a4 4 0 0 0-3.5-3.8V7zm-1 6.5a2 2 0 0 1-2-2h-2a4 4 0 0 0 4 4V19h2v-3.5a4 4 0 0 0 4-4h-2a2 2 0 0 1-4 0z' },
  { path: '/calendar', label: '日历', icon: 'M7 2h2v2h6V2h2v2h3a1 1 0 0 1 1 1v15a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3V2zm-3 6v11h16V8H4zm3-1h10v2H7V7z' },
  { path: '/todo', label: '待办', icon: 'M4 4h16a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zm1 2v12h14V6H5zm3.5 2l3 3 5-5 1.4 1.4-6.4 6.4-3-3L8.5 8z' },
  { path: '/notes', label: '笔记', icon: 'M5 2h11l4 4v16a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zm1 2v16h12V7h-3V4H6zm10 9v2H8v-2h8zm0-4v2H8V9h8z' },
  { path: '/habits', label: '习惯', icon: 'M12 2c1.5 3.2 4.5 5 6 6.5 1.8 1.8 3 4.2 3 6.9A9 9 0 0 1 12 24 9 9 0 0 1 3 15.4c0-2.7 1.2-5.1 3-6.9C7.5 7 10.5 5.2 12 2zm0 4.6C10.8 8 8.4 9.7 6.9 11.3A6.9 6.9 0 0 0 5 15.4 7 7 0 0 0 12 22a7 7 0 0 0 7-6.6c0-1.7-.7-3.1-1.9-4.1C15.6 9.7 13.2 8 12 6.6zm-2 8.9a2 2 0 1 0 4 0c0-1.1-2-3-2-3s-2 1.9-2 3z' },
]
</script>

<template>
  <div class="workspace">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">穴</span>
        <div class="brand-text">
          <strong>OpenLair</strong>
          <span>个人工作台</span>
        </div>
      </div>

      <nav class="nav" aria-label="模块导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="is-active"
          exact-active-class="is-active"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path :d="item.icon" />
          </svg>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <span class="dot" aria-hidden="true"></span>
        <span>本地数据 · v0.1</span>
      </div>
    </aside>

    <main class="content">
      <header class="content-header">
        <div>
          <p class="eyebrow">OpenLair Workspace</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <time class="today">{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }) }}</time>
      </header>
      <RouterView />
    </main>
  </div>
</template>
