import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    username: localStorage.getItem('username') || '',
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async login(username, password) {
      const data = await authApi.login({ username, password })
      this.token = data.access_token
      this.username = data.username
      localStorage.setItem('token', this.token)
      localStorage.setItem('username', this.username)
    },
    async logout() {
      try {
        await authApi.logout()
      } catch (e) {
        /* ignore */
      }
      this.token = ''
      this.username = ''
      localStorage.removeItem('token')
      localStorage.removeItem('username')
    },
  },
})
