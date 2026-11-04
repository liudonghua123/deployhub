<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="side-brand">
        <span class="logo-mini">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 18 L12 5 L19 18" />
            <line x1="8.5" y1="13" x2="15.5" y2="13" />
          </svg>
        </span>
        <span class="side-name">DeployHub</span>
      </div>
      <nav class="side-nav">
        <p class="nav-group">运维</p>
        <router-link v-for="item in navMain" :key="item.path" :to="item.path" class="nav-item" active-class="active">
          <span class="nav-icon" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
        </router-link>
        <p class="nav-group">管理</p>
        <router-link v-for="item in navAdmin" :key="item.path" :to="item.path" class="nav-item" active-class="active">
          <span class="nav-icon" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="side-foot">
        <div class="user-chip">
          <div class="avatar">{{ auth.user?.username?.[0]?.toUpperCase() }}</div>
          <div class="user-meta">
            <div class="user-name">{{ auth.user?.username }}</div>
            <div class="user-role">{{ auth.roleLabel }}</div>
          </div>
        </div>
        <button class="btn-sm logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => { auth.refresh() })

const I = {
  dashboard: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/></svg>',
  apps: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 L21 7 v10 L12 22 L3 17 V7 Z"/><path d="M12 22 V12 M3 7 l9 5 9-5"/></svg>',
  ports: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 7 h13 M13 3 l4 4 -4 4 M20 17 H7 M11 13 l-4 4 4 4"/></svg>',
  terminal: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8 l4 4 -4 4 M11 16 h8"/><rect x="2" y="3" width="20" height="18" rx="3"/></svg>',
  nginx: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 L21 7 v10 L12 22 L3 17 V7 Z"/></svg>',
  users: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20 c0-3.6 2.9-6 6.5-6 s6.5 2.4 6.5 6 M16 4 a3.5 3.5 0 0 1 0 7 M17.5 14 c2.6.6 4 2.7 4 6"/></svg>',
  settings: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3 M12 19v3 M2 12h3 M19 12h3 M4.9 4.9l2.1 2.1 M17 17l2.1 2.1 M19.1 4.9 L17 7 M7 17 l-2.1 2.1"/></svg>',
}

const navMain = computed(() => {
  const base = [
    { path: '/dashboard', icon: I.dashboard, label: '仪表盘' },
    { path: '/apps', icon: I.apps, label: '应用管理' },
    { path: '/ports', icon: I.ports, label: '端口监听' },
  ]
  if (auth.can('operator')) {
    base.push({ path: '/terminal', icon: I.terminal, label: '在线终端' })
    base.push({ path: '/nginx', icon: I.nginx, label: 'Nginx 管理' })
  }
  return base
})

const navAdmin = computed(() => [
  { path: '/users', icon: I.users, label: '用户权限' },
  { path: '/settings', icon: I.settings, label: '设置' },
])

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; height: 100vh; height: 100dvh; }
.sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--bg-soft);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 20px 12px 16px;
}
.side-brand { display: flex; align-items: center; gap: 10px; padding: 2px 10px 22px; }
.logo-mini {
  width: 30px; height: 30px; background: var(--accent); border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(77, 159, 255, 0.35);
}
.side-name { font-weight: 700; font-size: 15px; letter-spacing: -0.02em; }
.side-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.nav-group {
  font-size: 10.5px; font-weight: 600; color: var(--ink-faint);
  letter-spacing: 0.08em; padding: 14px 12px 6px;
}
.nav-item {
  display: flex; align-items: center; gap: 11px;
  padding: 8px 12px; border-radius: 8px;
  color: var(--ink-dim); font-size: 13.5px;
  transition: background 0.2s var(--ease), color 0.2s var(--ease);
}
.nav-item:hover { background: var(--bg-hover); color: var(--ink); text-decoration: none; }
.nav-item.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.nav-icon { width: 18px; text-align: center; display: flex; align-items: center; justify-content: center; }
.side-foot { border-top: 1px solid var(--border); padding-top: 14px; }
.user-chip { display: flex; align-items: center; gap: 10px; padding: 0 6px; }
.avatar {
  width: 32px; height: 32px; border-radius: 10px;
  background: var(--bg-hover); border: 1px solid var(--border-strong);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: var(--accent);
}
.user-name { font-size: 13px; font-weight: 600; }
.user-role { font-size: 11px; color: var(--ink-faint); }
.logout-btn { width: 100%; margin-top: 12px; }
.main { flex: 1; overflow-y: auto; }

@media (max-width: 860px) {
  .sidebar { width: 60px; padding: 14px 8px; }
  .side-name, .nav-item span:last-child, .user-meta, .nav-group { display: none; }
  .side-brand { justify-content: center; padding-bottom: 14px; }
  .nav-item { justify-content: center; padding: 10px; }
  .logout-btn { padding: 5px; font-size: 11px; }
}
</style>
