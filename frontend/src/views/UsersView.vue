<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>用户与权限</h2>
        <p>基于 RBAC 的三级角色：管理员 · 运维 · 访客</p>
      </div>
      <button v-if="auth.isAdmin" class="btn-primary" @click="openCreate">+ 新建用户</button>
    </div>

    <div class="role-cards">
      <div class="panel role-card">
        <div class="role-head"><span class="badge badge-err">admin</span><b>管理员</b></div>
        <p>全部权限：用户管理、应用删除、nginx restart 等高危操作</p>
      </div>
      <div class="panel role-card">
        <div class="role-head"><span class="badge badge-warn">operator</span><b>运维</b></div>
        <p>应用的创建/启停/部署、nginx 配置编辑与 reload、在线终端</p>
      </div>
      <div class="panel role-card">
        <div class="role-head"><span class="badge badge-info">viewer</span><b>访客</b></div>
        <p>只读：查看应用状态、端口、日志、部署记录</p>
      </div>
    </div>

    <div class="panel">
      <table>
        <thead><tr><th>用户</th><th>角色</th><th>状态</th><th>创建时间</th><th v-if="auth.isAdmin">操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td><b>{{ u.username }}</b><span v-if="u.username === auth.user?.username" class="dim" style="margin-left:6px">(我)</span></td>
            <td>
              <select v-if="auth.isAdmin && u.username !== 'admin'" :value="u.role" @change="updateRole(u, $event.target.value)" class="role-select">
                <option value="admin">管理员</option>
                <option value="operator">运维</option>
                <option value="viewer">访客</option>
              </select>
              <span v-else class="badge" :class="roleBadge(u.role)">{{ roleLabel(u.role) }}</span>
            </td>
            <td>
              <span class="badge" :class="u.enabled ? 'badge-ok' : 'badge-dim'">{{ u.enabled ? '正常' : '禁用' }}</span>
            </td>
            <td class="dim">{{ u.created_at }}</td>
            <td v-if="auth.isAdmin">
              <button class="btn-sm" @click="openEdit(u)">编辑</button>
              <button class="btn-sm btn-danger" style="margin-left:6px" :disabled="u.username === 'admin' || u.id === auth.user?.id" @click="delUser(u)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal" style="width:440px">
        <div class="modal-head"><h3>{{ editing ? '编辑用户' : '新建用户' }}</h3><button class="modal-close" @click="showModal = false">✕</button></div>
        <div class="modal-body">
          <label>用户名</label>
          <input v-model="form.username" :disabled="!!editing" />
          <label style="margin-top:14px">密码 {{ editing ? '（留空则不修改）' : '' }}</label>
          <input v-model="form.password" type="password" placeholder="至少 6 位" />
          <label style="margin-top:14px">角色</label>
          <select v-model="form.role">
            <option value="admin">管理员</option>
            <option value="operator">运维</option>
            <option value="viewer">访客</option>
          </select>
          <label style="margin-top:14px;display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" v-model="form.enabled" style="width:auto" /> 启用账号
          </label>
        </div>
        <div class="modal-foot">
          <button @click="showModal = false">取消</button>
          <button class="btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { toast } from '../toast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const users = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ username: '', password: '', role: 'viewer', enabled: true })

const roleLabel = (r) => ({ admin: '管理员', operator: '运维', viewer: '访客' }[r] || r)
const roleBadge = (r) => ({ admin: 'badge-err', operator: 'badge-warn', viewer: 'badge-info' }[r] || 'badge-dim')

async function load() {
  users.value = await api.get('/api/users')
}

function openCreate() {
  editing.value = null
  form.value = { username: '', password: '', role: 'viewer', enabled: true }
  showModal.value = true
}

function openEdit(u) {
  editing.value = u
  form.value = { username: u.username, password: '', role: u.role, enabled: u.enabled }
  showModal.value = true
}

async function save() {
  try {
    if (editing.value) {
      await api.put(`/api/users/${editing.value.id}`, form.value)
    } else {
      await api.post('/api/users', form.value)
    }
    toast('已保存', 'ok')
    showModal.value = false
    load()
  } catch (e) { toast(e.message, 'err') }
}

async function updateRole(u, role) {
  try {
    await api.put(`/api/users/${u.id}`, { username: u.username, role, enabled: u.enabled })
    toast(`已将 ${u.username} 设为 ${roleLabel(role)}`, 'ok')
  } catch (e) { toast(e.message, 'err') }
  load()
}

async function delUser(u) {
  if (!confirm(`确定删除用户 ${u.username} ？`)) return
  try {
    await api.delete(`/api/users/${u.id}`)
    toast('已删除', 'ok')
    load()
  } catch (e) { toast(e.message, 'err') }
}

onMounted(load)
</script>

<style scoped>
.role-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.role-card { padding: 16px 18px; }
.role-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.role-card p { font-size: 12.5px; color: var(--ink-dim); line-height: 1.6; }
.dim { color: var(--ink-faint); font-size: 12px; }
.role-select { width: auto; padding: 4px 10px; font-size: 12.5px; }

@media (max-width: 860px) { .role-cards { grid-template-columns: 1fr; } }
</style>
