import axios from 'axios'
import { clearSession, session } from '../session'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api', timeout: 20000 })

http.interceptors.request.use((config) => {
  const token = session.token
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || 'error'))
    }
    return body
  },
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.message || err.message || '网络错误'
    if (status === 401 && !err.config?.url?.endsWith('/auth/login')) {
      clearSession()
      ElMessage.error('登录已过期，请重新登录')
      window.dispatchEvent(new Event('auth-expired'))
    } else if (!(status === 404 && err.config?.silentNotFound)) {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (data) => http.post('/auth/login', data),
  logout: () => http.post('/auth/logout'),
  me: () => http.get('/auth/me'),
  changePassword: (data) => http.put('/auth/password', data),
}

export const dictApi = {
  list: (kind) => http.get(`/dict/${kind}`),
  create: (kind, data) => http.post(`/dict/${kind}`, data),
  update: (kind, id, data) => http.put(`/dict/${kind}/${id}`, data),
  remove: (kind, id) => http.delete(`/dict/${kind}/${id}`),
}

export const productApi = {
  list: (params) => http.get('/products', { params }),
  get: (id) => http.get(`/products/${id}`),
  getByCode: (code, options = {}) => http.get(`/products/by-code/${encodeURIComponent(code)}`, options),
  create: (data) => http.post('/products', data),
  update: (id, data) => http.put(`/products/${id}`, data),
  remove: (id) => http.delete(`/products/${id}`),
}

export const uploadApi = {
  image: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/upload/image', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

export const purchaseApi = {
  list: (params) => http.get('/purchases', { params }),
  create: (data) => http.post('/purchases', data),
  batch: (items) => http.post('/purchases/batch', { items }),
  update: (id, data) => http.put(`/purchases/${id}`, data),
  remove: (id) => http.delete(`/purchases/${id}`),
}

export const saleApi = {
  list: (params) => http.get('/sales', { params }),
  create: (data) => http.post('/sales', data),
  update: (id, data) => http.put(`/sales/${id}`, data),
  remove: (id) => http.delete(`/sales/${id}`),
}

export const stockApi = {
  list: (params) => http.get('/stock', { params }),
  current: (styleCode, size) => http.get('/stock/current', { params: { style_code: styleCode, size } }),
}

export const statsApi = {
  summary: (params) => http.get('/stats/summary', { params }),
  dailySales: (params) => http.get('/stats/daily-sales', { params }),
  categoryRank: (params) => http.get('/stats/category-rank', { params }),
}

export const systemApi = {
  lanUrl: (params) => http.get('/system/lan-url', { params }),
}

export async function downloadFile(path, filename, params) {
  const resp = await http.get(path, { responseType: 'blob', params })
  const blob = resp instanceof Blob ? resp : new Blob([resp])
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const documentApi = {
  list: (params) => http.get('/documents', { params }),
  get: (id) => http.get(`/documents/${id}`),
  create: (data, key) => http.post('/documents', data, { headers: { 'Idempotency-Key': key } }),
  void: (id, reason) => http.post(`/documents/${id}/void`, { reason }),
  preview: () => http.get('/documents/cost-preview'),
  recompute: (fingerprint) => http.post('/documents/cost-recompute', { fingerprint }),
  audit: (params) => http.get('/documents/audit', { params }),
}
export const backupApi = {
  status: () => http.get('/backups/status'),
  validate: (file) => { const data = new FormData(); data.append('file', file); return http.post('/backups/validate', data) },
  restore: (token) => http.post('/backups/restore', { token }),
  cancel: () => http.post('/backups/cancel'),
}
export default http
