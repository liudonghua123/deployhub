<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>设置</h2>
        <p>账号安全与系统信息</p>
      </div>
    </div>

    <div class="settings-grid">
      <div class="panel">
        <div class="panel-head"><h3>修改密码</h3></div>
        <div class="panel-body">
          <label>当前密码</label>
          <input v-model="pw.old_password" type="password" />
          <label style="margin-top:14px">新密码</label>
          <input v-model="pw.new_password" type="password" placeholder="至少 6 位" />
          <button class="btn-primary" style="margin-top:18px" @click="changePw">保存新密码</button>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>系统信息</h3></div>
        <div class="panel-body info-list">
          <div class="info-row"><span>平台</span><b>DeployHub v1.0</b></div>
          <div class="info-row"><span>我的角色</span><b><span class="badge badge-info">{{ auth.roleLabel }}</span></b></div>
          <div class="info-row"><span>后端 API</span><b class="mono">/api/*</b></div>
          <div class="info-row"><span>Webhook 前缀</span><b class="mono small">/api/deploy/webhook/{应用名}</b></div>
          <div class="info-row"><span>应用工作区</span><b class="mono small">./workspaces/{应用名}</b></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const pw = ref({ old_password: '', new_password: '' })

async function changePw() {
  if (!pw.value.old_password || !pw.value.new_password) { toast('请填写完整', 'err'); return }
  if (pw.value.new_password.length < 6) { toast('新密码至少 6 位', 'err'); return }
  try {
    const r = await api.post('/api/users/change-password', pw.value)
    toast(r.message + '，其它设备需重新登录', 'ok')
    pw.value = { old_password: '', new_password: '' }
  } catch (e) { toast(e.message, 'err') }
}
</script>

<style scoped>
.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.info-list { padding: 8px 18px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-bottom: 1px solid rgba(42,49,57,.5); gap: 12px; }
.info-row:last-child { border-bottom: none; }
.info-row > span { color: var(--ink-dim); font-size: 12.5px; }
.mono { font-family: var(--mono); font-size: 12.5px; }
.small { font-size: 11.5px; }

@media (max-width: 860px) { .settings-grid { grid-template-columns: 1fr; } }
</style>
