<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-brand">
        <div class="logo-mark">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 18 L12 5 L19 18" />
            <line x1="8.5" y1="13" x2="15.5" y2="13" />
          </svg>
        </div>
        <h1>DeployHub</h1>
        <p>连接 GitHub 仓库，推送即部署</p>
      </div>
      <form @submit.prevent="submit">
        <label>用户名</label>
        <input v-model="username" placeholder="admin" autocomplete="username" autofocus />
        <label style="margin-top:14px">密码</label>
        <input v-model="password" type="password" placeholder="••••••••" autocomplete="current-password" />
        <p v-if="err" class="login-err" role="alert">{{ err }}</p>
        <button class="btn-primary login-btn" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>
      <div class="login-hint">
        <span>admin / admin123</span>
        <span>operator / operator123</span>
        <span>viewer / viewer123</span>
      </div>
    </div>
    <div class="login-aside">
      <div class="aside-item" v-for="f in features" :key="f.t">
        <span class="aside-key mono">{{ f.k }}</span>
        <div>
          <b>{{ f.t }}</b>
          <p>{{ f.d }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const err = ref('')
const loading = ref(false)

const features = [
  { k: 'git', t: '推送即部署', d: 'GitHub Webhook 触发流水线：拉取代码、执行初始化命令、自动重启' },
  { k: 'ps', t: '进程与端口', d: '实时查看每个应用的运行状态、监听端口与资源占用' },
  { k: 'conf', t: 'Nginx 在线管理', d: '站点配置编辑、语法检查、平滑重载，不离开浏览器' },
  { k: 'tty', t: '在线终端', d: '遇到问题时直接进入服务器 Shell 排查' },
]

async function submit() {
  if (!username.value || !password.value) { err.value = '请输入用户名和密码'; return }
  loading.value = true
  err.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 72px;
  padding: 32px;
}
.login-card {
  width: 380px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 40px 36px 28px;
  box-shadow: var(--shadow-lg);
}
.login-brand { margin-bottom: 30px; }
.logo-mark {
  width: 44px; height: 44px; margin-bottom: 16px;
  background: var(--accent);
  border-radius: 11px;
  display: flex; align-items: center; justify-content: center;
}
.login-brand h1 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.03em;
  background: linear-gradient(90deg, #ffffff 0%, #9b9b9b 130%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.login-brand p { color: var(--ink-dim); font-size: 13px; margin-top: 6px; }
.login-err { color: var(--err); font-size: 12.5px; margin-top: 10px; }
.login-btn { width: 100%; margin-top: 22px; padding: 10px; font-size: 14px; }
.login-hint {
  margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border);
  color: var(--ink-faint); font-size: 11.5px;
  display: flex; gap: 12px; flex-wrap: wrap;
}
.login-hint span { font-family: var(--mono); }

.login-aside { width: 320px; display: flex; flex-direction: column; gap: 28px; }
.aside-item { display: flex; gap: 14px; }
.aside-key {
  flex-shrink: 0;
  font-size: 11px; color: var(--accent);
  background: var(--accent-soft);
  padding: 4px 8px; border-radius: 6px;
  height: fit-content;
  margin-top: 2px;
}
.aside-item b { font-size: 14px; font-weight: 600; }
.aside-item p { color: var(--ink-dim); font-size: 12.5px; margin-top: 4px; line-height: 1.6; }

@media (max-width: 980px) {
  .login-aside { display: none; }
}
</style>
