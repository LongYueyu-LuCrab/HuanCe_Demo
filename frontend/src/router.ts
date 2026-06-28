import { createRouter, createWebHistory } from 'vue-router'
import { getMenuGroups } from './permissions'
import { useSession } from './stores/session'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('./layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { menuKey: 'dashboard' } },
        { path: 'orders', name: 'orders', component: () => import('./views/OrdersView.vue'), meta: { menuKey: 'orders' } },
        { path: 'schedule', name: 'schedule', component: () => import('./views/ScheduleView.vue'), meta: { menuKey: 'schedule' } },
        { path: 'samples', name: 'samples', component: () => import('./views/SamplesView.vue'), meta: { menuKey: 'samples' } },
        { path: 'labs/:lab', name: 'lab', component: () => import('./views/LabView.vue') },
        { path: 'outsource', name: 'outsource', component: () => import('./views/OutsourceView.vue'), meta: { menuKey: 'outsource' } },
        { path: 'reports', name: 'reports', component: () => import('./views/ReportsView.vue'), meta: { menuKey: 'reports' } },
        { path: 'finance', name: 'finance', component: () => import('./views/FinanceView.vue'), meta: { menuKey: 'invoice' } },
        { path: 'audit', name: 'audit', component: () => import('./views/AuditView.vue'), meta: { menuKey: 'audit' } },
        { path: 'employees', name: 'employees', component: () => import('./views/EmployeesView.vue'), meta: { menuKey: 'employees' } },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const session = useSession()
  await session.bootstrap()
  if (to.meta.public) {
    return session.isAuthenticated.value ? '/dashboard' : true
  }
  if (!session.isAuthenticated.value) return '/login'

  const visibleKeys = new Set(getMenuGroups(session.state.user).flatMap((group) => group.items.map((item) => item.key)))
  const menuKey = to.meta.menuKey as string | undefined
  if (menuKey && !visibleKeys.has(menuKey)) {
    const firstPath = getMenuGroups(session.state.user)[0]?.items[0]?.path || '/dashboard'
    return firstPath
  }
  if (to.name === 'lab') {
    const lab = to.params.lab
    const key = lab === 'jiangyin' ? 'jiangyin' : 'suzhou'
    if (!visibleKeys.has(key)) {
      const firstPath = getMenuGroups(session.state.user)[0]?.items[0]?.path || '/dashboard'
      return firstPath
    }
  }
  return true
})
