// Shared reactive state avoids router/API/store circular imports.
import { reactive } from 'vue'
export const session = reactive({
  token: localStorage.getItem('token') || '',
  username: localStorage.getItem('username') || '',
  mustChange: localStorage.getItem('mustChange') === '1',
  demo: false,
  notice: '',
})
export function clearSession() {
  session.token = ''; session.username = ''; session.mustChange = false
  for (const key of ['token', 'username', 'mustChange']) localStorage.removeItem(key)
}
export function saveSession(data) {
  session.token = data.access_token || session.token
  session.username = data.username
  session.mustChange = !!data.must_change_password
  session.demo = !!data.demo
  session.notice = data.upgrade_notice || ''
  localStorage.setItem('token', session.token)
  localStorage.setItem('username', session.username)
  localStorage.setItem('mustChange', session.mustChange ? '1' : '0')
}
