const BASE = ''

function getToken() {
  return localStorage.getItem('dh_token') || ''
}

export function setToken(token) {
  localStorage.setItem('dh_token', token)
}

export function clearToken() {
  localStorage.removeItem('dh_token')
}

async function request(method, url, body) {
  const opts = { method, headers: {} }
  if (getToken()) opts.headers['Authorization'] = 'Bearer ' + getToken()
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(BASE + url, opts)
  if (res.status === 401) {
    clearToken()
    if (!location.hash.includes('/login')) location.hash = '#/login'
    throw new Error('登录已失效')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `请求失败 (${res.status})`)
  return data
}

export const api = {
  get: (url) => request('GET', url),
  post: (url, body) => request('POST', url, body),
  put: (url, body) => request('PUT', url, body),
  delete: (url) => request('DELETE', url),
}

export function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}${BASE}${path}?token=${encodeURIComponent(getToken())}`
}
