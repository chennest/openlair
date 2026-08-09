import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/request'

const router = createRouter({
  history: createWebHistory(),
  // 切换路由后回到顶部：避免旧页面滚动位置残留导致新页面被强制 clamp 跳动
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', name: 'login', component: () => import('../modules/auth/index.vue'), meta: { title: '登录' } },
    { path: '/', name: 'overview', component: () => import('../modules/overview/index.vue'), meta: { title: '总揽' } },
    { path: '/ledger', name: 'ledger', component: () => import('../modules/ledger/index.vue'), meta: { title: '记账' } },
    { path: '/calendar', name: 'calendar', component: () => import('../modules/calendar/index.vue'), meta: { title: '日历' } },
    { path: '/todo', name: 'todo', component: () => import('../modules/todo/index.vue'), meta: { title: '待办' } },
    { path: '/notes', name: 'notes', component: () => import('../modules/notes/index.vue'), meta: { title: '笔记' } },
    { path: '/habits', name: 'habits', component: () => import('../modules/habits/index.vue'), meta: { title: '习惯' } },
    { path: '/profile', name: 'profile', component: () => import('../modules/profile/index.vue'), meta: { title: '个人信息' } },
  ],
})

// 全局守卫：未登录 → /login（带 redirect）；已登录访问 /login → /
router.beforeEach((to) => {
  const authed = !!getToken()
  if (to.path === '/login') {
    return authed ? { path: '/' } : true
  }
  if (!authed) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

export default router
