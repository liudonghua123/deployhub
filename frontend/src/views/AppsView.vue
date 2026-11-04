<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>应用管理</h2>
        <p>管理部署应用：GitHub 仓库、启动命令、进程控制</p>
      </div>
      <button v-if="auth.can('operator')" class="btn-primary" @click="openCreate">+ 新建应用</button>
    </div>

    <div v-if="loading && !apps.length" class="panel empty"><div class="empty-icon">⟳</div>加载中…</div>
    <div v-else-if="apps.length" class="app-grid">
      <div v-for="a in apps" :key="a.id" class="panel app-card" @click="$router.push('/apps/' + a.id)">
        <div class="app-card-head">
          <div class="app-title">
            <span :class="a.status?.running ? 'dot dot-ok' : 'dot dot-idle'"></span>
            <b>{{ a.name }}</b>
          </div>
          <span class="badge" :class="a.status?.running ? 'badge-ok' : 'badge-dim'">{{ a.status?.running ? '运行中' : '已停止' }}</span>
        </div>
        <div class="app-repo mono">{{ a.repo_url || '本地应用（未绑定仓库）' }}</div>
        <div class="app-meta">
          <span class="meta-item"><span class="meta-k">分支</span>{{ a.branch }}</span>
          <span class="meta-item"><span class="meta-k">端口</span>{{ a.listen_ports?.length ? a.listen_ports.join(', ') : '—' }}</span>
          <span class="meta-item"><span class="meta-k">PID</span>{{ a.status?.pid || '—' }}</span>
        </div>
        <div class="app-actions" @click.stop>
          <button class="btn-sm btn-ok" :disabled="a.status?.running || !auth.can('operator')" @click="act(a, 'start')">启动</button>
          <button class="btn-sm btn-danger" :disabled="!a.status?.running || !auth.can('operator')" @click="act(a, 'stop')">停止</button>
          <button class="btn-sm" :disabled="!auth.can('operator')" @click="act(a, 'restart')">重启</button>
          <button class="btn-sm" :disabled="!auth.can('operator')" @click="deploy(a)" style="margin-left:auto">{{ deploying === a.id ? '部署中…' : '⇩ 部署' }}</button>
        </div>
      </div>
    </div>
    <div v-else class="panel empty"><div class="empty-icon">◈</div>暂无应用，创建第一个吧</div>

    <!-- create/edit modal -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal modal-wide">
        <div class="modal-head">
          <h3>{{ editing ? '编辑应用' : '新建应用' }}</h3>
          <button class="modal-close" @click="showModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div><label>应用名称 *</label><input v-model="form.name" :disabled="editing" placeholder="my-app" /></div>
            <div><label>分支</label><input v-model="form.branch" placeholder="main" /></div>
            <div class="full"><label>GitHub 仓库地址</label><input v-model="form.repo_url" placeholder="git@github.com:user/repo.git 或 https://github.com/user/repo.git" /></div>
            <div class="full"><label>部署目录（留空自动分配 ./workspaces/应用名）</label><input v-model="form.deploy_dir" placeholder="/srv/apps/my-app" /></div>
            <div><label>初始运行命令（每次部署后执行，如 npm install）</label><input v-model="form.init_command" placeholder="npm install" /></div>
            <div><label>启动命令</label><input v-model="form.start_command" placeholder="npm run start" /></div>
            <div class="full"><label>描述</label><input v-model="form.description" placeholder="应用简介" /></div>
            <div class="full">
              <label>环境变量（JSON）</label>
              <textarea v-model="envText" rows="3" class="mono-input" placeholder='{"PORT": "3000", "NODE_ENV": "production"}'></textarea>
            </div>
            <div class="full check-row">
              <label style="margin:0;display:flex;align-items:center;gap:8px;cursor:pointer">
                <input type="checkbox" v-model="form.auto_deploy" style="width:auto" /> 开启 GitHub Webhook 自动部署
              </label>
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button @click="showModal = false">取消</button>
          <button class="btn-primary" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const apps = ref([])
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const deploying = ref(0)
const envText = ref('{}')
const loading = ref(true)
let timer = null

const emptyForm = { name: '', repo_url: '', branch: 'main', deploy_dir: '', init_command: '', start_command: '', description: '', auto_deploy: true }
const form = ref({ ...emptyForm })

async function load() {
  try { apps.value = await api.get('/api/apps') } catch (e) { console.error(e) } finally { loading.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { ...emptyForm }
  envText.value = '{}'
  showModal.value = true
}

function openEdit(a) {
  editing.value = a
  form.value = { ...a }
  envText.value = JSON.stringify(a.env || {}, null, 0)
  showModal.value = true
}
defineExpose({ openEdit })

async function save() {
  if (!form.value.name.trim()) { toast('请输入应用名', 'err'); return }
  let env = {}
  try { env = JSON.parse(envText.value || '{}') } catch { toast('环境变量不是合法 JSON', 'err'); return }
  saving.value = true
  try {
    const body = { ...form.value, env }
    if (editing.value) await api.put(`/api/apps/${editing.value.id}`, body)
    else await api.post('/api/apps', body)
    toast('已保存')
    showModal.value = false
    load()
  } catch (e) { toast(e.message, 'err') } finally { saving.value = false }
}

async function act(a, action) {
  try {
    const r = await api.post(`/api/apps/${a.id}/action`, { action })
    toast(r.message, r.ok ? 'ok' : 'err')
    load()
  } catch (e) { toast(e.message, 'err') }
}

async function deploy(a) {
  deploying.value = a.id
  try {
    const r = await api.post(`/api/deploy/${a.id}`)
    toast(r.message, 'ok')
    setTimeout(load, 1500)
  } catch (e) { toast(e.message, 'err') } finally { deploying.value = 0 }
}

onMounted(() => { load(); timer = setInterval(load, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.app-card { padding: 18px; cursor: pointer; transition: border-color 0.15s, transform 0.12s; }
.app-card:hover { border-color: #3a4654; transform: translateY(-2px); }
.app-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.app-title { display: flex; align-items: center; gap: 4px; font-size: 15px; }
.app-repo { font-size: 11.5px; color: var(--ink-faint); margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.app-meta { display: flex; gap: 18px; margin-bottom: 16px; flex-wrap: wrap; }
.meta-item { font-size: 12.5px; color: var(--ink); }
.meta-k { color: var(--ink-faint); margin-right: 6px; }
.app-actions { display: flex; gap: 8px; border-top: 1px solid var(--border); padding-top: 14px; }
.mono { font-family: var(--mono); }
.check-row { display: flex; align-items: center; }
</style>
