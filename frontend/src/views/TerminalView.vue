<template>
  <div class="page terminal-page">
    <div class="page-head">
      <div>
        <h2>在线终端
          <span class="badge" :class="connected ? 'badge-ok' : 'badge-err'" style="margin-left:8px;vertical-align:3px">
            {{ connected ? '● 已连接' : '○ 未连接' }}
          </span>
        </h2>
        <p>服务器 Shell，仅运维及以上角色可用</p>
      </div>
      <button @click="connect">{{ connected ? '重新连接' : '连接' }}</button>
    </div>
    <div class="panel term-panel">
      <div ref="termEl" class="term-box"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { wsUrl } from '../api'
import '@xterm/xterm/css/xterm.css'

const termEl = ref(null)
const connected = ref(false)
let term = null, ws = null, fit = null

function connect() {
  if (ws) { ws.close(); ws = null }
  term.reset()
  ws = new WebSocket(wsUrl('/api/ports/terminal'))
  ws.onopen = () => { connected.value = true; term.writeln('\x1b[32m✔ 已连接服务器 shell\x1b[0m\r\n') }
  ws.onclose = () => { connected.value = false; term.writeln('\r\n\x1b[31m✕ 连接已断开\x1b[0m') }
  ws.onmessage = (ev) => term.write(ev.data)
  ws.onerror = () => { connected.value = false }
}

onMounted(() => {
  term = new Terminal({
    fontFamily: "'JetBrains Mono', 'Cascadia Code', Consolas, monospace",
    fontSize: 13.5,
    theme: {
      background: '#0a0e13', foreground: '#c9d5e0',
      cursor: '#2f81f7', selectionBackground: 'rgba(47,129,247,.3)',
      black: '#0d1117', red: '#f85149', green: '#3fb950', yellow: '#d29922',
      blue: '#2f81f7', magenta: '#bc8cff', cyan: '#39c5cf', white: '#e6edf3',
    },
    cursorBlink: true,
  })
  fit = new FitAddon()
  term.loadAddon(fit)
  term.open(termEl.value)
  fit.fit()
  term.onData((data) => { if (ws && ws.readyState === 1) ws.send(data) })
  connect()
  window.addEventListener('resize', doFit)
})

function doFit() { try { fit && fit.fit() } catch {} }
onUnmounted(() => { window.removeEventListener('resize', doFit); if (ws) ws.close(); term && term.dispose() })
</script>

<style scoped>
.terminal-page { display: flex; flex-direction: column; height: calc(100vh - 0px); max-width: none; }
.term-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; margin-bottom: 20px; }
.term-box { flex: 1; padding: 10px 12px; background: #0a0e13; border-radius: 0 0 10px 10px; min-height: 0; }
.term-box .xterm { height: 100%; }
</style>
