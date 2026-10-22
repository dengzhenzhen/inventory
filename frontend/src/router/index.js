import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

window.addEventListener('auth-expired', () => router.replace('/login'))

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'purchase-entry', component: () => import('../views/PurchaseEntry.vue'), meta: { title: '进货录入' } },
      { path: 'purchase-list', component: () => import('../views/PurchaseList.vue'), meta: { title: '进货记录' } },
      { path: 'sale-create', component: () => import('../views/SaleCreate.vue'), meta: { title: '销售开单' } },
      { path: 'sale-list', component: () => import('../views/SaleList.vue'), meta: { title: '销售记录' } },
      { path: 'stock', component: () => import('../views/Stock.vue'), meta: { title: '库存查询' } },
      { path: 'products', component: () => import('../views/Products.vue'), meta: { title: '商品档案' } },
      { path: 'reports', component: () => import('../views/Reports.vue'), meta: { title: '统计报表' } },
      { path: 'documents', component: () => import('../views/DocumentCenter.vue'), meta: { title: '单据 / 退货 / 盘点' } },
      { path: 'settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return { path: '/login' }
  if (auth.isLoggedIn && auth.mustChange && to.path !== '/settings') return { path: '/settings' }
  if (to.path === '/login' && auth.isLoggedIn) return { path: '/dashboard' }
  return true
})

export default router
