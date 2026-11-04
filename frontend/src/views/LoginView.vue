<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-brand">
        <div class="logo-mark">▲</div>
        <h1>DeployHub</h1>
        <p>GitHub 自动部署 · 应用运维 · Nginx 管理</p>
      </div>
      <form @submit.prevent="submit">
        <label>用户名</label>
        <input v-model="username" placeholder="admin" autocomplete="username" />
        <label style="margin-top:14px">密码</label>
        <input v-model="password" type="password" placeholder="••••••••" autocomplete="current-password" />
        <p v-if="err" class="login-err">{{ err }}</p>
        <button class="btn-primary login-btn" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>
      <div class="login-hint">
        默认账号：admin / admin123 · operator / operator123 · viewer / viewer123
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const err = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) { err.value = '请输入用户名和密码'; return }
  loading.value = true
  err.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse 60% 50% at 70% 20%, rgba(47, 129, 247, 0.08), transparent),
    radial-gradient(ellipse 50% 40% at 20% 80%, rgba(63, 185, 80, 0.05), transparent),
    var(--bg);
}
.login-card {
  width: 380px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px 36px 28px;
}
.login-brand { text-align: center; margin-bottom: 30px; }
.logo-mark {
  width: 46px; height: 46px; margin: 0 auto 14px;
  background: var(--accent);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; color: #fff;
}
.login-brand h1 { font-size: 22px; letter-spacing: -0.02em; }
.login-brand p { color: var(--ink-dim); font-size: 12.5px; margin-top: 6px; }
.login-err { color: var(--err); font-size: 12.5px; margin-top: 10px; }
.login-btn { width: 100%; margin-top: 22px; padding: 10px; font-size: 14px; }
.login-hint {
  margin-top: 22px; padding-top: 16px; border-top: 1px solid var(--border);
  color: var(--ink-faint); font-size: 11.5px; text-align: center; line-height: 1.7;
}
</style>
