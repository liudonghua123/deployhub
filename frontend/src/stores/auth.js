import { defineStore } from 'pinia'
import { api } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('dh_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    isAdmin: (s) => s.user?.role === 'admin',
    isOperator: (s) => ['admin', 'operator'].includes(s.user?.role),
    roleLabel: (s) => ({ admin: '管理员', operator: '运维', viewer: '访客' }[s.user?.role] || s.user?.role),
  },
  actions: {
    async login(username, password) {
      const data = await api.post('/api/auth/login', { username, password })
      this.user = data.user
      localStorage.setItem('dh_user', JSON.stringify(data.user))
      localStorage.setItem('dh_token', data.token)
      return data.user
    },
    async refresh() {
      try {
        this.user = await api.get('/api/auth/me')
        localStorage.setItem('dh_user', JSON.stringify(this.user))
      } catch { /* handled by api */ }
    },
    logout() {
      this.user = null
      localStorage.removeItem('dh_user')
      localStorage.removeItem('dh_token')
    },
    can(level) {
      const levels = { viewer: 1, operator: 2, admin: 3 }
      return (levels[this.user?.role] || 0) >= (levels[level] || 99)
    },
  },
})
