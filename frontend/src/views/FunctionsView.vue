<template>
  <div class="page functions-page">
    <!-- 函数列表视图 -->
    <template v-if="!currentFn">
      <div class="page-head">
        <div>
          <h2>Functions</h2>
          <p>版本化运行目标：在线编辑、发布切换、一键回滚</p>
        </div>
        <div class="head-actions" v-if="auth.can('operator')">
          <button class="btn-primary" @click="showCreate = true">+ 新建函数</button>
        </div>
      </div>

      <div class="fn-grid">
        <div v-for="fn in fns" :key="fn.id" class="panel fn-card" @click="openFn(fn)">
          <div class="fn-card-head">
            <span class="fn-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            </span>
            <b class="fn-name mono">{{ fn.name }}</b>
            <span class="badge" :class="fn.running ? 'badge-ok' : 'badge-dim'">{{ fn.running ? '运行中' : '未运行' }}</span>
          </div>
          <p class="fn-desc">{{ fn.description || '无描述' }}</p>
          <div class="fn-meta">
            <span class="badge badge-info">{{ fn.runtime }}</span>
            <span class="dim small">v{{ fn.active_version || '—' }} 激活</span>
            <span class="dim small">{{ fn.version_count }} 个版本</span>
            <span class="fn-arrow">→</span>
          </div>
        </div>
        <div v-if="!fns.length && !loading" class="empty" style="grid-column: 1/-1; padding: 60px 0">
          <div class="empty-icon">⬢</div>
          <p>还没有函数。点击右上角「新建函数」开始。</p>
        </div>
      </div>
    </template>

    <!-- 函数详情视图 -->
    <template v-else>
      <div class="page-head">
        <div>
          <h2>
            <button class="back-btn" @click="closeFn" title="返回列表">←</button>
            <span class="mono">{{ currentFn.name }}</span>
            <span class="badge" :class="fnRunning ? 'badge-ok' : 'badge-dim'" style="margin-left:8px;vertical-align:3px">{{ fnRunning ? '运行中' : '未运行' }}</span>
            <span v-if="currentFn.active_version" class="badge badge-info" style="margin-left:5px;vertical-align:3px">v{{ currentFn.active_version }} 激活</span>
          </h2>
          <p>{{ currentFn.description || `${currentFn.runtime} · ${currentFn.run_command}` }}</p>
        </div>
        <div class="head-actions">
          <template v-if="auth.can('operator')">
            <button class="btn-ok" v-if="!fnRunning" :disabled="!currentFn.active_version" @click="fnStart">启动</button>
            <button class="btn-danger" v-else @click="fnStop">停止</button>
            <button @click="rollback" :disabled="currentFn.active_version <= 1">回滚</button>
            <button class="btn-primary" :disabled="!editorDirty" @click="saveAsVersion">保存为新版本</button>
          </template>
          <button v-if="auth.can('admin')" class="btn-danger" @click="destroyFn">删除函数</button>
        </div>
      </div>

      <div class="fn-layout">
        <!-- 左：版本时间线 -->
        <div class="panel version-panel">
          <div class="panel-head"><h3>版本</h3><span class="badge badge-dim">{{ versions.length }}</span></div>
          <div class="version-list">
            <div v-for="v in versions" :key="v.version"
                 class="version-item"
                 :class="{ active: v.version === currentFn.active_version, viewing: viewVersion === v.version }"
                 @click="viewVersionFn(v)">
              <span class="v-badge mono">v{{ v.version }}</span>
              <div class="v-info">
                <div class="v-label">{{ v.label || '(无说明)' }} <span v-if="v.version === currentFn.active_version" class="badge badge-ok">激活</span></div>
                <div class="v-meta">{{ v.created_by }} · {{ v.created_at }} · {{ v.file_count }} 文件</div>
              </div>
              <button v-if="auth.can('operator') && v.version !== currentFn.active_version"
                      class="btn-sm v-pub" @click.stop="publish(v.version)">发布</button>
            </div>
            <div v-if="!versions.length" class="empty" style="padding:30px">暂无版本</div>
          </div>
        </div>

        <!-- 右：代码编辑器 -->
        <div class="panel editor-panel">
          <div class="panel-head">
            <div class="file-tabs">
              <button v-for="f in Object.keys(files)" :key="f"
                      class="file-tab mono" :class="{ on: activeFile === f }"
                      @click="switchFile(f)">{{ f.split('/').pop() }}</button>
              <button v-if="canEdit" class="file-tab file-add" @click="addFile" title="新增文件">+</button>
            </div>
            <div class="editor-state">
              <span v-if="editorDirty" class="badge badge-warn">未保存</span>
              <span v-else-if="viewVersion" class="badge badge-dim">查看 v{{ viewVersion }}</span>
              <span v-if="canEdit" class="badge badge-ok">可编辑</span>
              <span v-else class="badge badge-dim">只读</span>
            </div>
          </div>
          <div class="editor-wrap">
            <textarea ref="editorEl"></textarea>
          </div>
          <div v-if="execOutput" class="exec-output">
            <div class="exec-head">
              <span class="badge" :class="execOk ? 'badge-ok' : 'badge-err'">exit {{ execCode }}</span>
              <button class="btn-sm" @click="execOutput = ''">关闭</button>
            </div>
            <pre>{{ execOutput }}</pre>
          </div>
        </div>
      </div>

      <div class="panel log-panel">
        <div class="panel-head">
          <h3>运行日志</h3>
          <div class="log-actions">
            <button class="btn-sm" :disabled="!fnRunning" @click="refreshLogs">刷新</button>
          </div>
        </div>
        <div class="log-box" ref="logBox">{{ logText || '暂无日志' }}</div>
      </div>
    </template>

    <!-- 新建函数模态框 -->
    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head"><h3>新建函数</h3><button class="modal-close" @click="showCreate = false">✕</button></div>
        <div class="modal-body">
          <div class="form-row"><label>函数名</label><input v-model="createForm.name" class="mono-input" placeholder="my-function" @keydown.enter="create" /></div>
          <div class="form-row"><label>运行时</label>
            <select v-model="createForm.runtime">
              <option value="python">python</option>
              <option value="node">node</option>
            </select>
          </div>
          <div class="form-row"><label>描述</label><input v-model="createForm.description" placeholder="可选" /></div>
          <p class="form-hint">创建后进入编辑器，首个版本需手动发布才会运行。</p>
        </div>
        <div class="modal-foot">
          <button @click="showCreate = false">取消</button>
          <button class="btn-primary" @click="create">创建</button>
        </div>
      </div>
    </div>

    <!-- 新增文件模态框 -->
    <div v-if="showAddFile" class="modal-mask" @click.self="showAddFile = false">
      <div class="modal">
        <div class="modal-head"><h3>新增文件</h3><button class="modal-close" @click="showAddFile = false">✕</button></div>
        <div class="modal-body">
          <div class="form-row"><label>文件路径</label><input v-model="newFileName" class="mono-input" placeholder="utils/helper.py" @keydown.enter="confirmAddFile" /></div>
        </div>
        <div class="modal-foot">
          <button @click="showAddFile = false">取消</button>
          <button class="btn-primary" @click="confirmAddFile">添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import CodeMirror from 'codemirror'
import 'codemirror/mode/python/python'
import 'codemirror/mode/javascript/javascript'
import 'codemirror/addon/mode/simple'
import 'codemirror/lib/codemirror.css'
import { api } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const fns = ref([])
const loading = ref(false)
const currentFn = ref(null)
const versions = ref([])
const viewVersion = ref(null)      // 正在查看的版本号（null=草稿/最新）
const files = ref({})              // 当前编辑器中的文件树
const activeFile = ref('')
const editorDirty = ref(false)
const canEdit = ref(false)
const execOutput = ref('')
const execOk = ref(false)
const execCode = ref(0)
const logText = ref('')
const fnRunning = ref(false)
const showCreate = ref(false)
const showAddFile = ref(false)
const newFileName = ref('')
const createForm = ref({ name: '', runtime: 'python', description: '' })
const editorEl = ref(null)
const logBox = ref(null)
let cm = null
let timer = null

const MODE_MAP = { py: 'python', js: 'javascript', json: { name: 'javascript', json: true }, txt: 'null', md: 'null' }

function cmMode(path) {
  const ext = path.split('.').pop().toLowerCase()
  return MODE_MAP[ext] || 'null'
}

async function loadList() {
  loading.value = true
  try { fns.value = await api.get('/api/functions') } catch (e) { toast(e.message, 'err') } finally { loading.value = false }
}

async function openFn(fn) {
  currentFn.value = fn
  await loadDetail()
}

function closeFn() {
  currentFn.value = null
  viewVersion.value = null
  files.value = {}
  editorDirty.value = false
  logText.value = ''
  execOutput.value = ''
  loadList()
}

async function loadDetail() {
  const fn = currentFn.value
  versions.value = await api.get(`/api/functions/${fn.id}/versions`)
  fnRunning.value = (await api.get(`/api/functions/${fn.id}`)).running
  // 默认查看激活版本；无激活版本则草稿态
  if (fn.active_version) {
    await viewVersionFn(versions.value.find(v => v.version === fn.active_version))
  } else {
    files.value = {}
    viewVersion.value = null
    canEdit.value = auth.can('operator')
    editorDirty.value = false
    await initEditor(true)
  }
  refreshLogs()
}

async function viewVersionFn(v) {
  if (!v) return
  const data = await api.get(`/api/functions/${currentFn.value.id}/versions/${v.version}`)
  viewVersion.value = v.version
  files.value = data.files || {}
  const isLatest = versions.value.length && v.version === versions.value[0].version
  canEdit.value = auth.can('operator') && isLatest
  editorDirty.value = false
  activeFile.value = data.entry_file || Object.keys(files.value)[0] || ''
  await initEditor()
  if (!files.value[activeFile.value] && Object.keys(files.value).length) {
    switchFile(Object.keys(files.value)[0])
  }
}

async function initEditor(fresh = false) {
  await nextTick()
  if (!cm) {
    cm = CodeMirror.fromTextArea(editorEl.value, {
      lineNumbers: true, indentUnit: 4, lineWrapping: true, theme: 'default',
    })
    cm.on('change', () => { editorDirty.value = true })
  }
  cm.setOption('mode', cmMode(activeFile.value) || 'null')
  cm.setValue(files.value[activeFile.value] ?? '')
  cm.setOption('readOnly', !canEdit.value)
  cm.refresh()
}

function switchFile(f) {
  if (cm && activeFile.value) files.value[activeFile.value] = cm.getValue()
  activeFile.value = f
  if (cm) {
    cm.setOption('mode', cmMode(f) || 'null')
    cm.setValue(files.value[f] ?? '')
    cm.setOption('readOnly', !canEdit.value)
    cm.refresh()
  }
}

function addFile() { showAddFile.value = true; newFileName.value = '' }

async function confirmAddFile() {
  const name = newFileName.value.trim()
  if (!name) return
  if (files.value[name] !== undefined) { toast('文件已存在', 'err'); return }
  files.value[name] = ''
  showAddFile.value = false
  switchFile(name)
  editorDirty.value = true
}

async function saveAsVersion() {
  if (!cm) return
  if (activeFile.value) files.value[activeFile.value] = cm.getValue()
  const entry = currentFn.value.entry_file
  if (files.value[entry] === undefined) { toast(`入口文件 ${entry} 必须存在`, 'err'); return }
  const label = prompt2(`版本说明（v${(versions.value[0]?.version || 0) + 1}）:`) || ''
  try {
    const v = await api.post(`/api/functions/${currentFn.value.id}/versions`, {
      files: files.value, label,
      run_command: currentFn.value.run_command,
      entry_file: entry,
    })
    toast(`已创建 v${v.version}`, 'ok')
    editorDirty.value = false
    await loadDetail()
    const nv = versions.value.find(x => x.version === v.version)
    if (nv) await viewVersionFn(nv)
  } catch (e) { toast(e.message, 'err') }
}

// 简单的行内 prompt 替代：用 label 直接留空（避免 window.prompt）
function prompt2() { return '' }

async function publish(version) {
  try {
    const r = await api.post(`/api/functions/${currentFn.value.id}/versions/${version}/publish`)
    toast(r.message, 'ok')
    await loadDetail()
  } catch (e) { toast(e.message, 'err') }
}

async function rollback() {
  try {
    const r = await api.post(`/api/functions/${currentFn.value.id}/rollback`)
    toast(r.message, 'ok')
    await loadDetail()
  } catch (e) { toast(e.message, 'err') }
}

async function fnStart() {
  try { const r = await api.post(`/api/functions/${currentFn.value.id}/start`); toast(r.message, 'ok'); fnRunning.value = true } catch (e) { toast(e.message, 'err') }
}

async function fnStop() {
  try { const r = await api.post(`/api/functions/${currentFn.value.id}/stop`); toast(r.message, 'ok'); fnRunning.value = false } catch (e) { toast(e.message, 'err') }
}

async function destroyFn() {
  if (!confirm(`确定删除函数「${currentFn.value.name}」？\n\n所有版本代码与运行状态将一并移除，不可恢复。`)) return
  try {
    await api.delete(`/api/functions/${currentFn.value.id}`)
    toast('函数已删除', 'ok')
    closeFn()
  } catch (e) { toast(e.message, 'err') }
}

async function refreshLogs() {
  try {
    const r = await api.get(`/api/functions/${currentFn.value.id}/logs?tail=200`)
    logText.value = r.lines.join('\n')
    nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
  } catch {}
}

async function create() {
  const name = createForm.value.name.trim()
  if (!name) { toast('请输入函数名', 'err'); return }
  try {
    const fn = await api.post('/api/functions', createForm.value)
    toast('已创建', 'ok')
    showCreate.value = false
    createForm.value = { name: '', runtime: 'python', description: '' }
    await loadList()
    openFn(fns.value.find(f => f.id === fn.id) || fn)
  } catch (e) { toast(e.message, 'err') }
}

onMounted(() => {
  loadList()
  timer = setInterval(async () => {
    if (currentFn.value) {
      try { fnRunning.value = (await api.get(`/api/functions/${currentFn.value.id}`)).running } catch {}
    }
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.functions-page { max-width: none; }
.fn-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.fn-card { cursor: pointer; transition: transform 0.15s var(--ease, ease), box-shadow 0.15s; }
.fn-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.fn-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.fn-icon { display: inline-flex; color: var(--accent); }
.fn-name { font-size: 14.5px; }
.fn-desc { font-size: 12.5px; color: var(--ink-dim); margin-bottom: 10px; min-height: 18px; }
.fn-meta { display: flex; align-items: center; gap: 8px; }
.fn-arrow { margin-left: auto; color: var(--ink-faint); }
.back-btn { background: none; border: none; color: var(--ink-dim); cursor: pointer; font-size: 16px; padding: 0 6px 0 0; }
.back-btn:hover { color: var(--ink); }

.fn-layout { display: grid; grid-template-columns: 320px 1fr; gap: 16px; margin-bottom: 16px; }
.version-list { overflow-y: auto; max-height: 420px; }
.version-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; cursor: pointer;
  border-bottom: 1px solid rgba(49,49,49,.6);
  border-left: 2px solid transparent;
  transition: background 0.12s;
}
.version-item:hover { background: rgba(255,255,255,.03); }
.version-item.viewing { background: var(--bg-hover); border-left-color: var(--ink-faint); }
.version-item.active { border-left-color: var(--ok); }
.v-badge { font-size: 12px; color: var(--accent); background: var(--accent-soft); padding: 2px 8px; border-radius: 4px; flex-shrink: 0; }
.v-info { flex: 1; min-width: 0; }
.v-label { font-size: 12.5px; display: flex; align-items: center; gap: 6px; }
.v-meta { font-size: 11px; color: var(--ink-faint); margin-top: 2px; }
.v-pub { flex-shrink: 0; }

.editor-panel { display: flex; flex-direction: column; overflow: hidden; min-height: 420px; }
.file-tabs { display: flex; gap: 2px; flex-wrap: wrap; }
.file-tab {
  background: none; border: none; color: var(--ink-dim);
  font-size: 12px; padding: 5px 10px; cursor: pointer;
  border-radius: 6px; transition: all 0.12s;
}
.file-tab:hover { color: var(--ink); background: var(--bg-hover); }
.file-tab.on { color: var(--accent); background: var(--accent-soft); }
.file-add { color: var(--ink-faint); font-weight: bold; }
.editor-state { display: flex; gap: 6px; align-items: center; }
.editor-wrap { flex: 1; padding: 10px 14px; min-height: 340px; display: flex; }
.editor-wrap .CodeMirror { flex: 1; }
.editor-wrap textarea { display: none; }
.exec-output { border-top: 1px solid var(--border); padding: 10px 16px; }
.exec-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.exec-output pre { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
.log-panel .log-box { max-height: 240px; }
.form-row { margin-bottom: 12px; }
.form-row label { display: block; font-size: 12px; color: var(--ink-dim); margin-bottom: 5px; }
.form-row input, .form-row select {
  width: 100%; padding: 8px 11px;
  background: var(--bg-inset); border: 1px solid var(--border);
  border-radius: 8px; color: var(--ink); font-size: 13px; outline: none;
}
.form-row input:focus { border-color: var(--accent); }
.form-hint { font-size: 11.5px; color: var(--ink-faint); }

@media (max-width: 900px) {
  .fn-layout { grid-template-columns: 1fr; }
}
</style>
