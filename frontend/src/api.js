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
    localStorage.removeItem('dh_user')
    if (!location.hash.includes('/login')) {
      const path = location.hash.replace(/^#/, '') || '/dashboard'
      location.hash = '#/login?redirect=' + encodeURIComponent(path)
    }
    throw new Error('登录已失效，请重新登录')
  }
  if (res.status === 502 || res.status === 503) {
    throw new Error('服务暂时不可用，请稍后重试')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `请求失败 (${res.status})`)
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
