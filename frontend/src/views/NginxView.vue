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
          <h3 class="mono">{{ current || '选择左侧文件' }}<span v-if="dirty" class="badge badge-warn" style="margin-left:8px">未保存</span></h3>
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

    <!-- 新建配置模态框 -->
    <div v-if="showNew" class="modal-mask" @click.self="showNew = false">
      <div class="modal">
        <h3>新建配置文件</h3>
        <p class="modal-sub">输入文件名，保存时自动创建。示例：my-site.conf</p>
        <input
          v-model="newName"
          class="modal-input mono"
          placeholder="my-site.conf"
          @keydown.enter="confirmNew"
          @keydown.esc="showNew = false"
        />
        <div class="modal-actions">
          <button class="btn-sm" @click="showNew = false">取消</button>
          <button class="btn-sm btn-primary" @click="confirmNew">创建</button>
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
const showNew = ref(false)
const newName = ref('')
const editorEl = ref(null)
let cm = null
let dirty = false

function markDirty() { dirty = true }

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
  if (dirty && !confirm('当前文件有未保存的修改，切换将丢失。继续？')) return
  try {
    const data = await api.get(`/api/nginx/configs/${name}`)
    current.value = name
    testOutput.value = ''
    await nextTick()
    if (!cm) {
      cm = CodeMirror.fromTextArea(editorEl.value, {
        mode: 'nginx', lineNumbers: true, indentUnit: 4, lineWrapping: true,
      })
      cm.on('change', markDirty)
    }
    cm.setValue(data.content)
    dirty = false
  } catch (e) { toast(e.message, 'err') }
}

function newConf() { showNew.value = true; newName.value = '' }

function confirmNew() {
  const name = newName.value.trim()
  if (!name) return
  if (!/^[-a-zA-Z0-9_.]+$/.test(name)) { toast('文件名仅允许字母、数字、- _ .', 'err'); return }
  const safe = name.endsWith('.conf') ? name : name + '.conf'
  if (configs.value.some(c => c.name === safe)) { toast('同名配置文件已存在', 'err'); return }
  showNew.value = false
  current.value = safe
  testOutput.value = ''
  nextTick(() => {
    if (!cm) {
      cm = CodeMirror.fromTextArea(editorEl.value, { mode: 'nginx', lineNumbers: true, indentUnit: 4, lineWrapping: true })
    }
    cm.setValue('# ' + safe + '\nserver {\n    listen 80;\n    server_name example.com;\n\n    location / {\n        proxy_pass http://127.0.0.1:3000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n    }\n}\n')
    dirty = false
  })
  loadList()
}

async function saveConf() {
  if (!cm) return
  saving.value = true
  try {
    await api.put(`/api/nginx/configs/${current.value}`, { content: cm.getValue() })
    dirty = false
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
.nginx-layout { display: grid; grid-template-columns: 260px 1fr; gap: 16px; height: calc(100dvh - 150px); }
.conf-list { overflow-y: auto; }
.conf-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 16px; cursor: pointer; border-bottom: 1px solid rgba(49,49,49,.6);
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

.modal-mask {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,.55);
  display: flex; align-items: center; justify-content: center;
  animation: fadeIn 0.15s ease;
}
.modal {
  width: min(420px, calc(100vw - 48px));
  background: var(--bg-raised);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 22px 24px;
  box-shadow: var(--shadow-lg);
  animation: popIn 0.18s var(--ease, ease);
}
.modal h3 { font-size: 15px; margin-bottom: 4px; }
.modal-sub { font-size: 12px; color: var(--ink-dim); margin-bottom: 14px; }
.modal-input {
  width: 100%; padding: 9px 12px;
  background: var(--bg-inset); border: 1px solid var(--border);
  border-radius: 8px; color: var(--ink); font-size: 13px;
  outline: none; transition: border-color 0.15s;
}
.modal-input:focus { border-color: var(--accent); }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
@keyframes fadeIn { from { opacity: 0; } }
@keyframes popIn { from { opacity: 0; transform: scale(0.96) translateY(6px); } }

@media (max-width: 900px) {
  .nginx-layout { grid-template-columns: 1fr; height: auto; }
  .editor-wrap { min-height: 300px; }
}
</style>
