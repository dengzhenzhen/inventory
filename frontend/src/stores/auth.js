import { defineStore } from 'pinia'
import { authApi } from '../api'
import { session, clearSession, saveSession } from '../session'
export const useAuthStore = defineStore('auth', {
  state: () => ({ session }),
  getters: {
    token: () => session.token,
    username: () => session.username,
    isLoggedIn: () => !!session.token,
    mustChange: () => session.mustChange,
  },
  actions: {
    async login(username, password) { saveSession(await authApi.login({ username, password })) },
    async logout() { try { await authApi.logout() } finally { clearSession() } },
  },
})
