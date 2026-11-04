<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>仪表盘</h2>
        <p>应用运行状态与系统概览</p>
      </div>
      <button class="btn-primary" @click="$router.push('/apps')">+ 新建应用</button>
    </div>

    <div class="stat-grid">
      <div class="stat-card panel">
        <div class="stat-label">运行中应用</div>
        <div class="stat-value stat-ok">{{ runningCount }}<span class="stat-sub">/ {{ apps.length }}</span></div>
      </div>
      <div class="stat-card panel">
        <div class="stat-label">监听端口</div>
        <div class="stat-value">{{ ports.length }}</div>
      </div>
      <div class="stat-card panel">
        <div class="stat-label">Nginx 站点配置</div>
        <div class="stat-value">{{ nginxConfigs.length }}</div>
      </div>
      <div class="stat-card panel">
        <div class="stat-label">近 24h 部署</div>
        <div class="stat-value">{{ recentDeploys.length }}</div>
      </div>
    </div>

    <div class="dash-cols">
      <div class="panel">
        <div class="panel-head"><h3>应用状态</h3><router-link to="/apps" style="font-size:12.5px">全部 →</router-link></div>
        <table v-if="apps.length">
          <thead><tr><th>应用</th><th>状态</th><th>端口</th><th>运行时长</th></tr></thead>
          <tbody>
            <tr v-for="a in apps" :key="a.id" style="cursor:pointer" @click="$router.push('/apps/' + a.id)">
              <td><b>{{ a.name }}</b></td>
              <td>
                <span :class="a.status?.running ? 'dot dot-ok' : 'dot dot-idle'"></span>
                {{ a.status?.running ? '运行中' : '已停止' }}
              </td>
              <td><span v-for="p in a.listen_ports" :key="p" class="badge badge-info" style="margin-right:4px">{{ p }}</span><span v-if="!a.listen_ports?.length" class="dim">—</span></td>
              <td class="dim">{{ fmtUptime(a.status?.uptime) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty"><div class="empty-icon">◈</div>还没有应用，点击右上角创建</div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>最近部署</h3></div>
        <table v-if="recentDeploys.length">
          <thead><tr><th>时间</th><th>状态</th><th>提交</th></tr></thead>
          <tbody>
            <tr v-for="d in recentDeploys" :key="d.id">
              <td class="dim">{{ d.created_at }}</td>
              <td><span class="badge" :class="d.status === 'success' ? 'badge-ok' : d.status === 'failed' ? 'badge-err' : 'badge-warn'">{{ d.status === 'success' ? '成功' : d.status === 'failed' ? '失败' : '进行中' }}</span></td>
              <td class="mono dim">{{ d.commit_msg || d.commit || '手动操作' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty"><div class="empty-icon">⇩</div>暂无部署记录</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

const apps = ref([])
const ports = ref([])
const nginxConfigs = ref([])
const recentDeploys = ref([])
let timer = null

const runningCount = computed(() => apps.value.filter(a => a.status?.running).length)

function fmtUptime(s) {
  if (!s) return '—'
  if (s < 60) return s + ' 秒'
  if (s < 3600) return Math.floor(s / 60) + ' 分钟'
  return Math.floor(s / 3600) + ' 小时 ' + Math.floor((s % 3600) / 60) + ' 分'
}

async function load() {
  try {
    apps.value = await api.get('/api/apps')
    ports.value = await api.get('/api/ports')
    nginxConfigs.value = await api.get('/api/nginx/configs').catch(() => [])
    const deps = []
    for (const a of apps.value.slice(0, 3)) {
      try { deps.push(...await api.get(`/api/deploy/${a.id}/history?limit=5`)) } catch {}
    }
    recentDeploys.value = deps.sort((a, b) => b.id - a.id).slice(0, 8)
  } catch (e) { console.error(e) }
}

onMounted(() => { load(); timer = setInterval(load, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
.stat-card { padding: 18px 20px; }
.stat-label { font-size: 12px; color: var(--ink-dim); margin-bottom: 8px; }
.stat-value { font-size: 30px; font-weight: 650; letter-spacing: -0.02em; }
.stat-ok { color: var(--ok); }
.stat-sub { font-size: 15px; color: var(--ink-faint); font-weight: 400; margin-left: 4px; }
.dash-cols { display: grid; grid-template-columns: 1.3fr 1fr; gap: 16px; }
.dim { color: var(--ink-dim); }
.mono { font-family: var(--mono); font-size: 12px; }

@media (max-width: 960px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .dash-cols { grid-template-columns: 1fr; }
}
</style>
