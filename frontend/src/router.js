import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('./views/LayoutView.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
      { path: 'apps', name: 'apps', component: () => import('./views/AppsView.vue') },
      { path: 'apps/:id', name: 'app-detail', component: () => import('./views/AppDetailView.vue') },
      { path: 'ports', name: 'ports', component: () => import('./views/PortsView.vue') },
      { path: 'terminal', name: 'terminal', component: () => import('./views/TerminalView.vue') },
      { path: 'nginx', name: 'nginx', component: () => import('./views/NginxView.vue') },
      { path: 'users', name: 'users', component: () => import('./views/UsersView.vue') },
      { path: 'settings', name: 'settings', component: () => import('./views/SettingsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.isLoggedIn) return '/dashboard'
})

export default router
