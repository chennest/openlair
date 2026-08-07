<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { setToken, setUser, getUser } from './api/request'
import { authApi, type AuthUser } from './modules/auth/api'

const route = useRoute()
const router = useRouter()
const pageTitle = computed(() => (route.meta.title as string) || '总揽')

// ---------- 登录态：路由变化时从 localStorage 刷新（登录/登出后生效） ----------
const user = ref<AuthUser | null>(getUser() as AuthUser | null)
watch(
  () => route.path,
  () => {
    user.value = getUser() as AuthUser | null
  },
)

async function logout() {
  try {
    await authApi.logout()
  } catch {
    // token 已失效也无妨，本地照常清理
  }
  setToken(null)
  setUser(null)
  user.value = null
  router.push('/login')
}

/** /login 独立全屏页（无侧边导航与底栏） */
const isAuthPage = computed(() => route.path === '/login')

const navItems = [
  { path: '/', label: '总揽', icon: ['M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'] },
  { path: '/ledger', label: '记账', icon: ['M21 12V7H5a2 2 0 0 1 0-4h14v4', 'M3 5v14a2 2 0 0 0 2 2h16v-5', 'M18 12a2 2 0 0 0 0 4h4v-4Z'] },
  { path: '/calendar', label: '日历', icon: ['M8 2v4', 'M16 2v4', 'M3 10h18', 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z'] },
  { path: '/todo', label: '待办', icon: ['m9 11 3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'] },
  { path: '/notes', label: '笔记', icon: ['M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z', 'M14 2v4a2 2 0 0 0 2 2h4', 'M10 9H8', 'M16 13H8', 'M16 17H8'] },
  { path: '/habits', label: '习惯', icon: ['M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'] },
]

// Lucide 线性图标：24 网格、单笔画 1.75、currentColor（icons.md）
const iconProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': 1.75,
  'stroke-linecap': 'round' as const,
  'stroke-linejoin': 'round' as const,
}

// ---------- 响应式：桌面 / 手机布局切换 ----------
const isMobile = ref(false)
let mq: MediaQueryList | null = null
const mqHandler = (e: MediaQueryListEvent) => {
  isMobile.value = e.matches
}

onMounted(() => {
  mq = window.matchMedia('(max-width: 860px)')
  isMobile.value = mq.matches
  mq.addEventListener('change', mqHandler)
})

onBeforeUnmount(() => {
  mq?.removeEventListener('change', mqHandler)
})

// ---------- 手机端：左右滑动切换 Tab ----------
const currentIndex = computed(() => {
  const idx = navItems.findIndex((n) => n.path === route.path)
  return idx === -1 ? 0 : idx
})

let touchStartX = 0
let touchStartY = 0
let touchActive = false
const swipeDirection = ref<'forward' | 'back'>('forward')

// 手机顶栏 scroll-edge：内容滚动后才出现 hairline（design-system.md §4）
const mHeaderEl = ref<HTMLElement | null>(null)
function onMScroll(e: Event) {
  const el = e.currentTarget as HTMLElement
  mHeaderEl.value?.classList.toggle('scrolled', el.scrollTop > 8)
}

function onTouchStart(e: TouchEvent) {
  const t = e.touches[0]
  touchStartX = t.clientX
  touchStartY = t.clientY
  touchActive = true
}

function onTouchEnd(e: TouchEvent) {
  if (!touchActive) return
  touchActive = false
  const t = e.changedTouches[0]
  const dx = t.clientX - touchStartX
  const dy = t.clientY - touchStartY
  // 水平主导且超过阈值（48px）才触发，避免与纵向滚动冲突
  if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.2) return
  const target = dx < 0 ? currentIndex.value + 1 : currentIndex.value - 1
  if (target < 0 || target >= navItems.length) return
  swipeDirection.value = dx < 0 ? 'forward' : 'back'
  // 先滚回顶部再切换：避免旧页面滚动位置残留导致新页面被强制 clamp 跳动
  window.scrollTo(0, 0)
  router.push(navItems[target].path)
}

function goTo(index: number) {
  if (index === currentIndex.value) return
  swipeDirection.value = index > currentIndex.value ? 'forward' : 'back'
  // 先滚回顶部再切换：避免旧页面滚动位置残留导致新页面被强制 clamp 跳动
  window.scrollTo(0, 0)
  router.push(navItems[index].path)
}
</script>

<template>
  <!-- ============ 登录页（独立全屏，无导航壳） ============ -->
  <RouterView v-if="isAuthPage" />

  <!-- ============ 桌面布局（>860px） ============ -->
  <div v-else-if="!isMobile" class="workspace">
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
          <svg class="nav-icon" v-bind="iconProps" aria-hidden="true">
            <path v-for="(d, i) in item.icon" :key="i" :d="d" />
          </svg>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <template v-if="user">
          <span class="avatar" :style="{ background: user.avatarColor }">{{ user.name.slice(0, 1) }}</span>
          <span class="user-name">{{ user.name }}</span>
          <button class="logout-btn" title="退出登录" @click="logout">退出</button>
        </template>
        <template v-else>
          <span class="dot" aria-hidden="true"></span>
          <span>本地数据 · v0.1</span>
        </template>
      </div>
    </aside>

    <main class="content">
      <header class="content-header">
        <h1>{{ pageTitle }}</h1>
        <time class="today">{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }) }}</time>
      </header>
      <RouterView />
    </main>
  </div>

  <!-- ============ 手机布局（≤860px） ============ -->
  <div v-else class="m-workspace" @touchstart="onTouchStart" @touchend="onTouchEnd">
    <header class="m-header" ref="mHeaderEl">
      <span class="m-brand">穴</span>
      <strong>{{ pageTitle }}</strong>
      <time>{{ new Date().toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short' }) }}</time>
      <button
        v-if="user"
        class="m-avatar"
        :style="{ background: user.avatarColor }"
        :title="`${user.name} · 退出登录`"
        @click="logout"
      >{{ user.name.slice(0, 1) }}</button>
    </header>

    <main class="m-content" @scroll="onMScroll">
      <Transition :name="swipeDirection === 'forward' ? 'slide-fwd' : 'slide-back'" mode="out-in">
        <RouterView :key="route.path" />
      </Transition>
    </main>

    <nav class="m-tabbar" aria-label="底部导航">
      <button
        v-for="(item, index) in navItems"
        :key="item.path"
        class="m-tab"
        :class="{ 'is-active': route.path === item.path }"
        @click="goTo(index)"
      >
        <svg class="m-tab-icon" v-bind="iconProps" aria-hidden="true">
          <path v-for="(d, i) in item.icon" :key="i" :d="d" />
        </svg>
        <span>{{ item.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
/* ---------- 用户区（侧边栏底部） ---------- */
.avatar {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
}
.user-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-2);
  font-weight: 600;
}
.logout-btn {
  flex: 0 0 auto;
  padding: 5px 10px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  color: var(--text-3);
  background: var(--surface);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 160ms ease, border-color 160ms ease;
}
.logout-btn:hover {
  color: var(--heat);
  border-color: rgba(255, 107, 0, 0.4);
}

/* ---------- 用户区（手机顶栏右侧） ---------- */
.m-avatar {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: #fff;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
</style>
