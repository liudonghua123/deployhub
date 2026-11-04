<template>
  <div class="page" v-if="app">
    <div class="page-head">
      <div>
        <h2>
          <span :class="app.status?.running ? 'dot dot-ok' : 'dot dot-idle'"></span>
          {{ app.name }}
          <span class="badge" :class="app.status?.running ? 'badge-ok' : 'badge-dim'" style="margin-left:8px;vertical-align:3px">{{ app.status?.running ? '运行中' : '已停止' }}</span>
        </h2>
        <p>{{ app.description || (app.repo_url || '本地应用') }}</p>
      </div>
      <div class="head-actions">
        <template v-if="auth.can('operator')">
          <button class="btn-ok" :disabled="app.status?.running" @click="act('start')">启动</button>
          <button class="btn-danger" :disabled="!app.status?.running" @click="act('stop')">停止</button>
          <button @click="act('restart')">重启</button>
          <button class="btn-primary" @click="deploy">{{ deploying ? '部署中…' : '立即部署' }}</button>
          <button @click="showEdit = true">编辑</button>
        </template>
        <button v-if="auth.can('admin')" class="btn-danger" @click="destroy">删除</button>
      </div>
    </div>

    <div class="detail-grid">
      <div class="panel info-panel">
        <div class="panel-head"><h3>运行信息</h3></div>
        <div class="panel-body info-list">
          <div class="info-row"><span>PID</span><b class="mono">{{ app.status?.pid || '—' }}</b></div>
          <div class="info-row"><span>监听端口</span><b>
            <span v-for="p in listenPorts" :key="p" class="badge badge-info" style="margin-right:5px">{{ p }}</span>
            <span v-if="!listenPorts.length" class="dim">—</span>
          </b></div>
          <div class="info-row">
            <span>健康检查</span>
            <b>
              <span v-if="health.checking" class="badge badge-dim">检查中…</span>
              <span v-else-if="health.ok" class="badge badge-ok">✓ HTTP {{ health.status }}</span>
              <span v-else-if="health.done" class="badge badge-err" :title="health.error">✕ 无响应</span>
              <span v-else class="dim">—</span>
            </b>
          </div>
          <div class="info-row"><span>运行时长</span><b>{{ fmtUptime(app.status?.uptime) }}</b></div>
          <div class="info-row"><span>分支</span><b class="mono">{{ app.branch }}</b></div>
          <div class="info-row"><span>部署目录</span><b class="mono small">{{ app.deploy_dir }}</b></div>
          <div class="info-row"><span>启动命令</span><b class="mono small">{{ app.start_command || '—' }}</b></div>
          <div class="info-row"><span>Webhook</span>
            <b>
              <span class="badge" :class="app.auto_deploy ? 'badge-ok' : 'badge-dim'">{{ app.auto_deploy ? '已开启' : '关闭' }}</span>
            </b>
          </div>
          <div class="info-row webhook-row" v-if="app.auto_deploy">
            <span>Webhook URL</span>
            <b class="mono small selectable">{{ webhookUrl }}</b>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h3>部署历史</h3>
          <span class="badge badge-dim">{{ deployments.length }} 条</span>
        </div>
        <div class="dep-list">
          <div v-for="d in deployments" :key="d.id" class="dep-item" :class="{ open: openDep === d.id }" @click="toggleDep(d)">
            <span class="badge" :class="d.status === 'success' ? 'badge-ok' : d.status === 'failed' ? 'badge-err' : 'badge-warn'">
              {{ d.status === 'success' ? '✓ 成功' : d.status === 'failed' ? '✕ 失败' : '… 进行中' }}
            </span>
            <span class="dep-msg">{{ d.commit_msg || d.commit || '手动部署' }}</span>
            <span class="dep-time">{{ d.created_at }}</span>
          </div>
          <div v-if="!deployments.length" class="empty" style="padding:30px">暂无部署记录</div>
        </div>
        <div v-if="openDepLog" class="dep-log-wrap">
          <div class="log-box dep-log">{{ openDepLog }}</div>
        </div>
      </div>
    </div>

    <div class="panel log-panel">
      <div class="panel-head">
        <h3>实时日志</h3>
        <div class="log-actions">
          <button class="btn-sm" @click="autoScroll = !autoScroll">{{ autoScroll ? '⏸ 暂停滚动' : '▶ 自动滚动' }}</button>
          <button class="btn-sm" v-if="auth.can('operator')" @click="clearLogs">清空</button>
        </div>
      </div>
      <div class="log-box live-log" ref="logBox">{{ logText || '等待日志输出…' }}</div>
    </div>

    <!-- edit modal -->
    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="modal modal-wide">
        <div class="modal-head"><h3>编辑应用 · {{ app.name }}</h3><button class="modal-close" @click="showEdit = false">✕</button></div>
        <div class="modal-body">
          <div class="form-grid">
            <div><label>分支</label><input v-model="editForm.branch" /></div>
            <div><label>部署目录</label><input v-model="editForm.deploy_dir" /></div>
            <div class="full"><label>GitHub 仓库地址</label><input v-model="editForm.repo_url" /></div>
            <div><label>初始运行命令</label><input v-model="editForm.init_command" /></div>
            <div><label>启动命令</label><input v-model="editForm.start_command" /></div>
            <div class="full"><label>描述</label><input v-model="editForm.description" /></div>
            <div class="full"><label>环境变量（JSON）</label><textarea v-model="envText" rows="3" class="mono-input"></textarea></div>
          </div>
        </div>
        <div class="modal-foot">
          <button @click="showEdit = false">取消</button>
          <button class="btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api, wsUrl } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const app = ref(null)
const deployments = ref([])
const listenPorts = ref([])
const logText = ref('')
const deploying = ref(false)
const showEdit = ref(false)
const editForm = ref({})
const envText = ref('{}')
const openDep = ref(null)
const openDepLog = ref('')
const health = ref({ checking: false, ok: false, done: false, status: null, error: '' })
const logBox = ref(null)
const autoScroll = ref(true)
let ws = null
let timer = null

const webhookUrl = computed(() => {
  if (!app.value) return ''
  return `${location.origin}/api/deploy/webhook/${app.value.name}`
})

function fmtUptime(s) {
  if (!s) return '—'
  if (s < 60) return s + ' 秒'
  if (s < 3600) return Math.floor(s / 60) + ' 分钟'
  const h = Math.floor(s / 3600)
  return h + ' 小时 ' + Math.floor((s % 3600) / 60) + ' 分'
}

async function load() {
  const id = route.params.id
  app.value = await api.get(`/api/apps/${id}`)
  deployments.value = await api.get(`/api/deploy/${id}/history`)
  try {
    const all = await api.get('/api/apps')
    listenPorts.value = all.find(a => a.id === +id)?.listen_ports || []
  } catch {}
  checkHealth()
  if (!editForm.value.name && app.value) {
    editForm.value = { ...app.value }
    envText.value = JSON.stringify(app.value.env || {}, null, 0)
  }
}

async function checkHealth() {
  const ports = listenPorts.value
  if (!app.value?.status?.running || !ports.length) {
    health.value = { checking: false, ok: false, done: false, status: null, error: '' }
    return
  }
  health.value = { ...health.value, checking: true }
  try {
    const r = await api.post(`/api/apps/${route.params.id}/health`, { port: ports[0], path: '/' })
    health.value = { checking: false, ok: r.ok, done: true, status: r.status, error: r.error || '' }
  } catch (e) {
    health.value = { checking: false, ok: false, done: true, status: null, error: e.message }
  }
}

function connectWs() {
  ws = new WebSocket(wsUrl(`/api/logs/ws/${route.params.id}`))
  ws.onmessage = (ev) => {
    if (!ev.data) return
    logText.value = (logText.value + ev.data + '\n').split('\n').slice(-800).join('\n')
    if (autoScroll.value) nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
  }
  ws.onclose = () => setTimeout(() => { if (!ws || ws.readyState === 3) connectWs() }, 3000)
  ws.onerror = () => ws.close()
}

async function act(action) {
  try {
    const r = await api.post(`/api/apps/${route.params.id}/action`, { action })
    toast(r.message, r.ok ? 'ok' : 'err')
    load()
  } catch (e) { toast(e.message, 'err') }
}

async function deploy() {
  deploying.value = true
  try {
    const r = await api.post(`/api/deploy/${route.params.id}`)
    toast(r.message, 'ok')
    setTimeout(load, 1500)
  } catch (e) { toast(e.message, 'err') } finally { deploying.value = false }
}

async function save() {
  try { JSON.parse(envText.value || '{}') } catch { toast('环境变量不是合法 JSON', 'err'); return }
  try {
    await api.put(`/api/apps/${route.params.id}`, { ...editForm.value, name: app.value.name, env: JSON.parse(envText.value || '{}') })
    toast('已保存', 'ok')
    showEdit.value = false
    editForm.value = {}
    load()
  } catch (e) { toast(e.message, 'err') }
}

async function toggleDep(d) {
  if (openDep.value === d.id) { openDep.value = null; openDepLog.value = ''; return }
  const detail = await api.get(`/api/deploy/log/${d.id}`)
  openDep.value = d.id
  openDepLog.value = detail.log || '(无日志)'
}

async function clearLogs() {
  await api.delete(`/api/logs/${route.params.id}`)
  logText.value = ''
  toast('日志已清空', 'ok')
}

async function destroy() {
  if (!confirm(`确定删除应用「${app.value.name}」？\n\n该操作不可恢复：应用记录、运行状态将一并移除（部署目录与日志保留在磁盘）。`)) return
  try {
    await api.delete(`/api/apps/${route.params.id}`)
    toast('应用已删除', 'ok')
    location.hash = '#/apps'
  } catch (e) { toast(e.message, 'err') }
}

onMounted(() => { load(); connectWs(); timer = setInterval(load, 5000) })
onUnmounted(() => { clearInterval(timer); if (ws) ws.close() })
</script>

<style scoped>
.head-actions { display: flex; gap: 9px; flex-wrap: wrap; }
.detail-grid { display: grid; grid-template-columns: 380px 1fr; gap: 16px; margin-bottom: 16px; }
.info-list { padding: 8px 18px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(49,49,49,.6); gap: 12px; }
.info-row:last-child { border-bottom: none; }
.info-row > span { color: var(--ink-dim); font-size: 12.5px; flex-shrink: 0; }
.info-row > b { font-size: 13px; text-align: right; }
.mono { font-family: var(--mono); }
.small { font-size: 11.5px; }
.dim { color: var(--ink-faint); }
.selectable { user-select: all; cursor: text; }
.webhook-row { border-bottom: none !important; }
.dep-list { max-height: 260px; overflow-y: auto; }
.dep-item {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 18px; border-bottom: 1px solid rgba(49,49,49,.6);
  cursor: pointer; transition: background 0.12s;
}
.dep-item:hover, .dep-item.open { background: rgba(255,255,255,.03); }
.dep-msg { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dep-time { font-size: 11.5px; color: var(--ink-faint); flex-shrink: 0; }
.dep-log-wrap { border-top: 1px solid var(--border); }
.dep-log { border: none; border-radius: 0; max-height: 300px; }
.log-panel .live-log { min-height: 300px; max-height: 460px; margin: 14px 18px 18px; width: calc(100% - 36px); }
.log-actions { display: flex; gap: 8px; }

@media (max-width: 960px) {
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
