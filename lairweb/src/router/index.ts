import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: () => import('../modules/overview/index.vue'), meta: { title: '总揽' } },
    { path: '/ledger', name: 'ledger', component: () => import('../modules/ledger/index.vue'), meta: { title: '记账' } },
    { path: '/calendar', name: 'calendar', component: () => import('../modules/calendar/index.vue'), meta: { title: '日历' } },
    { path: '/todo', name: 'todo', component: () => import('../modules/todo/index.vue'), meta: { title: '待办' } },
    { path: '/notes', name: 'notes', component: () => import('../modules/notes/index.vue'), meta: { title: '笔记' } },
    { path: '/habits', name: 'habits', component: () => import('../modules/habits/index.vue'), meta: { title: '习惯' } },
  ],
})

export default router
