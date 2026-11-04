<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="side-brand">
        <span class="logo-mini">▲</span>
        <span class="side-name">DeployHub</span>
      </div>
      <nav class="side-nav">
        <router-link v-for="item in nav" :key="item.path" :to="item.path" class="nav-item" active-class="active">
          <span class="nav-icon">{{ item.icon }}</span>
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
        <button class="btn-sm" style="width:100%;margin-top:10px" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const nav = computed(() => {
  const base = [
    { path: '/dashboard', icon: '▦', label: '仪表盘' },
    { path: '/apps', icon: '◈', label: '应用管理' },
    { path: '/ports', icon: '⇌', label: '端口监听' },
  ]
  if (auth.can('operator')) {
    base.push({ path: '/terminal', icon: '⌨', label: '在线终端' })
    base.push({ path: '/nginx', icon: '⬢', label: 'Nginx 管理' })
  }
  base.push({ path: '/users', icon: '◉', label: '用户权限' })
  base.push({ path: '/settings', icon: '⚙', label: '设置' })
  return base
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; height: 100vh; }
.sidebar {
  width: 216px; flex-shrink: 0;
  background: var(--bg-soft);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 18px 12px;
}
.side-brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 20px; }
.logo-mini {
  width: 30px; height: 30px; background: var(--accent); border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 13px; flex-shrink: 0;
}
.side-name { font-weight: 650; font-size: 15px; letter-spacing: -0.01em; }
.side-nav { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.nav-item {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 12px; border-radius: 8px;
  color: var(--ink-dim); font-size: 13.5px;
  transition: background 0.13s, color 0.13s;
}
.nav-item:hover { background: var(--bg-hover); color: var(--ink); text-decoration: none; }
.nav-item.active { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
.nav-icon { width: 18px; text-align: center; font-size: 13px; }
.side-foot { border-top: 1px solid var(--border); padding-top: 14px; }
.user-chip { display: flex; align-items: center; gap: 10px; padding: 0 6px; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--bg-hover); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; color: var(--accent);
}
.user-name { font-size: 13px; font-weight: 500; }
.user-role { font-size: 11px; color: var(--ink-faint); }
.main { flex: 1; overflow-y: auto; }

@media (max-width: 860px) {
  .sidebar { width: 62px; padding: 14px 8px; }
  .side-name, .nav-item span:last-child, .user-meta { display: none; }
  .side-brand { justify-content: center; padding-bottom: 14px; }
  .nav-item { justify-content: center; padding: 10px; }
}
</style>
