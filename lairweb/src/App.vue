<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

const navItems: { path: string; label: string; icon: string[]; mobile?: boolean }[] = [
  { path: '/', label: '总揽', icon: ['M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'] },
  { path: '/ledger', label: '记账', icon: ['M21 12V7H5a2 2 0 0 1 0-4h14v4', 'M3 5v14a2 2 0 0 0 2 2h16v-5', 'M18 12a2 2 0 0 0 0 4h4v-4Z'] },
  { path: '/calendar', label: '日历', icon: ['M8 2v4', 'M16 2v4', 'M3 10h18', 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z'] },
  { path: '/todo', label: '待办', icon: ['m9 11 3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'] },
  { path: '/notes', label: '笔记', icon: ['M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z', 'M14 2v4a2 2 0 0 0 2 2h4', 'M10 9H8', 'M16 13H8', 'M16 17H8'] },
  { path: '/habits', label: '习惯', icon: ['M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'] },
  { path: '/assistant', label: 'AI 助手', icon: ['M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'] },
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
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  mq?.removeEventListener('change', mqHandler)
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})

// ---------- 手机端导航过滤（mobile: false 项不显示在底部 tabbar） ----------
const mobileNavItems = computed(() => navItems.filter((n) => n.mobile !== false))

// ---------- 手机端：左右滑动切换 Tab ----------
const mobileIndex = computed(() => {
  const idx = mobileNavItems.value.findIndex((n) => n.path === route.path)
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
  const items = mobileNavItems.value
  const curIdx = mobileIndex.value
  const target = dx < 0 ? curIdx + 1 : curIdx - 1
  if (target < 0 || target >= items.length) return
  swipeDirection.value = dx < 0 ? 'forward' : 'back'
  // 先滚回顶部再切换：避免旧页面滚动位置残留导致新页面被强制 clamp 跳动
  window.scrollTo(0, 0)
  router.push(items[target].path)
}

function goTo(idx: number) {
  const items = mobileNavItems.value
  const curIdx = mobileIndex.value
  if (idx === curIdx) return
  swipeDirection.value = idx > curIdx ? 'forward' : 'back'
  // 先滚回顶部再切换：避免旧页面滚动位置残留导致新页面被强制 clamp 跳动
  window.scrollTo(0, 0)
  router.push(items[idx].path)
}

// ---------- 手机端顶栏头像菜单（popover） ----------
const showMenu = ref(false)
const menuRef = ref<HTMLElement | null>(null)

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function closeMenu() {
  showMenu.value = false
}

function goProfile() {
  closeMenu()
  router.push('/profile')
}

// 菜单外点击关闭
function onDocClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    closeMenu()
  }
}

watch(showMenu, (val) => {
  if (val) {
    void nextTick(() => document.addEventListener('click', onDocClick))
  } else {
    document.removeEventListener('click', onDocClick)
  }
})

// 路由变化关闭菜单
watch(
  () => route.path,
  () => {
    closeMenu()
  },
)

// Escape 关闭
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && showMenu.value) {
    closeMenu()
  }
}
</script>

<template>
  <!-- ============ 登录页（独立全屏，无导航壳） ============ -->
  <RouterView v-if="isAuthPage" />

  <!-- ============ 桌面布局（>860px） ============ -->
  <div v-else-if="!isMobile" class="workspace">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">L</span>
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

    <main class="content" :class="{ 'is-assistant': route.path === '/assistant' }">
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
        <span class="m-brand">L</span>
      <strong>{{ pageTitle }}</strong>
      <time>{{ new Date().toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short' }) }}</time>
      <button
        v-if="user"
        class="m-avatar"
        :style="{ background: user.avatarColor }"
        @click.stop="toggleMenu"
      >{{ user.name.slice(0, 1) }}</button>
      <Transition name="menu-pop">
        <div v-if="user && showMenu" class="m-menu" ref="menuRef" @click.stop>
          <button class="m-menu-item" @click="goProfile">
            <svg class="m-menu-icon" v-bind="iconProps" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>个人信息</span>
          </button>
          <div class="m-menu-divider"></div>
          <button class="m-menu-item is-heat" @click="logout">
            <svg class="m-menu-icon" v-bind="iconProps" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      </Transition>
    </header>

    <main class="m-content" @scroll="onMScroll">
      <Transition :name="swipeDirection === 'forward' ? 'slide-fwd' : 'slide-back'" mode="out-in">
        <RouterView :key="route.path" />
      </Transition>
    </main>

    <nav class="m-tabbar" aria-label="底部导航" :style="{ gridTemplateColumns: `repeat(${mobileNavItems.length}, 1fr)` }">
      <button
        v-for="(item, index) in mobileNavItems"
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

/* ---------- 手机端头像菜单（popover / 玻璃；motion.md §5 materialize） ---------- */
.m-menu {
  position: absolute;
  top: calc(100% - 4px);
  right: 8px;
  z-index: 50;
  min-width: 160px;
  padding: 6px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-card);
  background: rgba(245, 245, 247, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  box-shadow: var(--sh-overlay);
}

.menu-pop-enter-active {
  transition: opacity 0.35s var(--ease-spring), transform 0.35s var(--ease-spring),
              backdrop-filter 0.35s var(--ease-spring), -webkit-backdrop-filter 0.35s var(--ease-spring);
}

.menu-pop-leave-active {
  transition: opacity 0.25s var(--ease-spring), transform 0.25s var(--ease-spring),
              backdrop-filter 0.25s var(--ease-spring), -webkit-backdrop-filter 0.25s var(--ease-spring);
}

.menu-pop-enter-from,
.menu-pop-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
  backdrop-filter: saturate(180%) blur(0px);
  -webkit-backdrop-filter: saturate(180%) blur(0px);
}

.m-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: 0;
  border-radius: var(--r-thumb);
  background: transparent;
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 160ms ease;
}

.m-menu-item:hover {
  background: var(--hover);
}

.m-menu-item.is-heat {
  color: var(--heat);
}

.m-menu-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  opacity: 0.8;
}

.m-menu-divider {
  height: 1px;
  margin: 3px 8px;
  background: var(--hairline);
}

/* 减少动效 / 透明度 / 对比度（motion.md §8） */
@media (prefers-reduced-motion: reduce) {
  .menu-pop-enter-active,
  .menu-pop-leave-active {
    transition: opacity 200ms ease;
  }
  .menu-pop-enter-from,
  .menu-pop-leave-to {
    transform: none;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}

@media (prefers-reduced-transparency: reduce) {
  .m-menu {
    background: #fff;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}

@media (prefers-contrast: more) {
  .m-menu {
    background: #fff;
    border: 1px solid rgba(0, 0, 0, 0.35);
  }
}

/* ════════════════════════════════════════════
   /assistant 页面：约束 .content 至视口，消除浏览器级纵向滚动
   ════════════════════════════════════════════ */
.content.is-assistant {
  height: 100dvh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* 保留水平 padding；底部 padding 归零 —— assistant 输入区自带底部间距 */
  padding-bottom: 0;
}
</style>
