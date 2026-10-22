import { beforeEach, expect, test, vi } from 'vitest'
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))
import { session, clearSession, saveSession } from '../src/session'
import { today } from '../src/utils'
import http from '../src/api'

beforeEach(() => { clearSession(); http.defaults.adapter = undefined })
test('local date remains correct in the early morning', () => {
  const d = new Date(2026, 9, 22, 1, 0)
  expect(today(d)).toBe('2026-10-22')
})
test('401 clears both reactive auth state and storage', async () => {
  saveSession({ access_token: 'old', username: 'admin', must_change_password: true })
  const expired = vi.fn(); window.addEventListener('auth-expired', expired)
  http.defaults.adapter = (config) => Promise.reject({ config, response: { status: 401, data: {} } })
  await expect(http.get('/stock')).rejects.toBeDefined()
  expect(session.token).toBe(''); expect(session.mustChange).toBe(false)
  expect(localStorage.getItem('token')).toBeNull(); expect(expired).toHaveBeenCalledOnce()
  window.removeEventListener('auth-expired', expired)
})
test('incorrect login does not masquerade as an expired session', async () => {
  const expired = vi.fn(); window.addEventListener('auth-expired', expired)
  http.defaults.adapter = (config) => Promise.reject({ config, response: { status: 401, data: { message: '账号或密码错误' } } })
  await expect(http.post('/auth/login', {})).rejects.toBeDefined()
  expect(expired).not.toHaveBeenCalled()
  window.removeEventListener('auth-expired', expired)
})
