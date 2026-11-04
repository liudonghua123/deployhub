<template>
  <div class="page nginx-page">
    <div class="page-head">
      <div>
        <h2>Nginx 管理</h2>
        <p>站点配置在线编辑、语法检查、reload / restart</p>
      </div>
      <div class="head-actions" v-if="auth.can('operator')">
        <button @click="testConf">⚡ 配置检查</button>
        <button @click="reloadNginx">Reload</button>
        <button v-if="auth.isAdmin" class="btn-danger" @click="restartNginx">Restart</button>
        <button class="btn-primary" @click="newConf">+ 新建配置</button>
      </div>
    </div>

    <div class="nginx-layout">
      <div class="panel conf-list-panel">
        <div class="panel-head"><h3>配置文件</h3><span class="badge badge-dim">{{ configs.length }}</span></div>
        <div class="conf-list">
          <div v-for="c in configs" :key="c.name" class="conf-item" :class="{ active: current === c.name }" @click="openConf(c.name)">
            <span class="conf-name mono">{{ c.name }}</span>
            <span class="conf-size">{{ fmtSize(c.size) }}</span>
          </div>
          <div v-if="!configs.length" class="empty" style="padding:32px">
            <div class="empty-icon">⬢</div>
            <template v-if="nginxError">{{ nginxError }}</template>
            <template v-else>目录下暂无 .conf 文件</template>
          </div>
        </div>
      </div>

      <div class="panel editor-panel">
        <div class="panel-head">
          <h3 class="mono">{{ current || '选择左侧文件' }}</h3>
          <div v-if="current && auth.can('operator')" class="editor-actions">
            <button class="btn-sm" @click="saveConf" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
            <button class="btn-sm btn-danger" v-if="auth.isAdmin" @click="delConf">删除</button>
          </div>
        </div>
        <div class="editor-wrap">
          <textarea ref="editorEl"></textarea>
        </div>
        <div v-if="testOutput" class="test-output" :class="testOk ? 't-ok' : 't-err'">
          <pre>{{ testOutput }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import CodeMirror from 'codemirror'
import 'codemirror/mode/nginx/nginx'
import 'codemirror/lib/codemirror.css'
import { api } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const configs = ref([])
const current = ref('')
const saving = ref(false)
const testOutput = ref('')
const testOk = ref(false)
const nginxError = ref('')
const editorEl = ref(null)
let cm = null

function fmtSize(n) {
  if (n < 1024) return n + ' B'
  return (n / 1024).toFixed(1) + ' KB'
}

async function loadList() {
  try {
    configs.value = await api.get('/api/nginx/configs')
    nginxError.value = ''
  } catch (e) { nginxError.value = e.message }
}

async function openConf(name) {
  try {
    const data = await api.get(`/api/nginx/configs/${name}`)
    current.value = name
    testOutput.value = ''
    await nextTick()
    if (!cm) {
      cm = CodeMirror.fromTextArea(editorEl.value, {
        mode: 'nginx', lineNumbers: true, indentUnit: 4, lineWrapping: true,
      })
    }
    cm.setValue(data.content)
  } catch (e) { toast(e.message, 'err') }
}

function newConf() {
  const name = prompt('新配置文件名（如 my-site.conf）:')
  if (!name) return
  const safe = name.endsWith('.conf') ? name : name + '.conf'
  current.value = safe
  testOutput.value = ''
  nextTick(() => {
    if (!cm) {
      cm = CodeMirror.fromTextArea(editorEl.value, { mode: 'nginx', lineNumbers: true, indentUnit: 4, lineWrapping: true })
    }
    cm.setValue('# ' + safe + '\nserver {\n    listen 80;\n    server_name example.com;\n\n    location / {\n        proxy_pass http://127.0.0.1:3000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n    }\n}\n')
  })
  loadList()
}

async function saveConf() {
  if (!cm) return
  saving.value = true
  try {
    await api.put(`/api/nginx/configs/${current.value}`, { content: cm.getValue() })
    toast('已保存，建议执行配置检查 + reload', 'ok')
    loadList()
  } catch (e) { toast(e.message, 'err') } finally { saving.value = false }
}

async function delConf() {
  if (!confirm(`确定删除 ${current.value} ？`)) return
  try {
    await api.delete(`/api/nginx/configs/${current.value}`)
    toast('已删除', 'ok')
    current.value = ''
    if (cm) cm.setValue('')
    loadList()
  } catch (e) { toast(e.message, 'err') }
}

async function testConf() {
  try {
    const r = await api.post('/api/nginx/test')
    testOk.value = r.ok
    testOutput.value = r.output
    toast(r.ok ? '配置检查通过' : '配置有误', r.ok ? 'ok' : 'err')
  } catch (e) { toast(e.message, 'err') }
}

async function reloadNginx() {
  try {
    const r = await api.post('/api/nginx/reload')
    toast(r.output || (r.ok ? '已重载' : '重载失败'), r.ok ? 'ok' : 'err')
  } catch (e) { toast(e.message, 'err') }
}

async function restartNginx() {
  if (!confirm('确定重启 nginx？会短暂中断服务。')) return
  try {
    const r = await api.post('/api/nginx/restart')
    toast(r.output || (r.ok ? '已重启' : '重启失败'), r.ok ? 'ok' : 'err')
  } catch (e) { toast(e.message, 'err') }
}

onMounted(loadList)
</script>

<style scoped>
.nginx-page { max-width: none; }
.nginx-layout { display: grid; grid-template-columns: 260px 1fr; gap: 16px; height: calc(100vh - 150px); }
.conf-list { overflow-y: auto; }
.conf-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 16px; cursor: pointer; border-bottom: 1px solid rgba(42,49,57,.5);
  transition: background 0.12s;
}
.conf-item:hover { background: rgba(255,255,255,.03); }
.conf-item.active { background: var(--accent-soft); }
.conf-item.active .conf-name { color: var(--accent); }
.conf-name { font-size: 12.5px; }
.conf-size { font-size: 11px; color: var(--ink-faint); }
.editor-panel { display: flex; flex-direction: column; overflow: hidden; }
.editor-wrap { flex: 1; padding: 14px 16px; min-height: 0; display: flex; }
.editor-wrap .CodeMirror { flex: 1; }
.editor-wrap textarea { display: none; }
.editor-actions { display: flex; gap: 8px; }
.test-output { border-top: 1px solid var(--border); padding: 10px 16px; }
.test-output pre { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; }
.t-ok { color: var(--ok); }
.t-err { color: var(--err); }
.mono { font-family: var(--mono); }

@media (max-width: 900px) {
  .nginx-layout { grid-template-columns: 1fr; height: auto; }
  .editor-wrap { min-height: 300px; }
}
</style>
