<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>端口监听</h2>
        <p>当前系统所有 TCP 监听端口，托管应用的端口已标记</p>
      </div>
      <div class="filter-row">
        <input v-model="filter" placeholder="筛选端口 / 进程 / 应用…" style="width:260px" />
        <label style="display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--ink-dim);cursor:pointer">
          <input type="checkbox" v-model="onlyApps" style="width:auto" /> 仅看托管应用
        </label>
      </div>
    </div>

    <div class="panel">
      <table v-if="filtered.length">
        <thead><tr><th>端口</th><th>地址</th><th>进程</th><th>PID</th><th>托管应用</th></tr></thead>
        <tbody>
          <tr v-for="p in filtered" :key="p.port + p.address + p.pid">
            <td><b class="mono">{{ p.port }}</b></td>
            <td class="mono dim">{{ p.address }}</td>
            <td class="mono">{{ p.process || '—' }}</td>
            <td class="mono dim">{{ p.pid || '—' }}</td>
            <td>
              <span v-if="p.app" class="badge badge-ok">◈ {{ p.app }}</span>
              <span v-else class="dim">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty"><div class="empty-icon">⇌</div>无匹配端口</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

const ports = ref([])
const filter = ref('')
const onlyApps = ref(false)
let timer = null

const filtered = computed(() => {
  let list = ports.value
  if (onlyApps.value) list = list.filter(p => p.app)
  const q = filter.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(p =>
    String(p.port).includes(q) || (p.process || '').toLowerCase().includes(q) || (p.app || '').toLowerCase().includes(q)
  )
})

async function load() {
  try { ports.value = await api.get('/api/ports') } catch {}
}
onMounted(() => { load(); timer = setInterval(load, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.mono { font-family: var(--mono); font-size: 12.5px; }
.dim { color: var(--ink-dim); }
.filter-row { display: flex; gap: 10px; }
</style>
