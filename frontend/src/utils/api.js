import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api`
    : '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(
            import.meta.env.VITE_API_URL
              ? `${import.meta.env.VITE_API_URL}/api/auth/refresh`
              : '/api/auth/refresh',
            null,
            { params: { refresh_token: refresh } }
          )
          localStorage.setItem('access_token', data.access_token)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          return api.request(error.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        localStorage.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  me:       ()     => api.get('/auth/me'),
  updateMode: (mode) => api.patch(`/auth/me/mode?mode=${mode}`),
}

// ─── Schema / Connections ─────────────────────────────────────────────────────
export const schemaAPI = {
  listConnections:  ()      => api.get('/schema/connections'),
  getConnections:   ()      => api.get('/schema/connections'),
  createConnection: (data)  => api.post('/schema/connections', data),
  refreshSchema:    (id)    => api.post(`/schema/connections/${id}/refresh-schema`),
  getSchema:        (id)    => api.get(`/schema/connections/${id}/schema`),
  deleteConnection: (id)    => api.delete(`/schema/connections/${id}`),
  connectDemo:      (name)  => api.post(`/schema/demo/${name}/connect`),
  previewTable:     (id, table, limit = 100) =>
    api.get(`/schema/connections/${id}/tables/${table}/preview?limit=${limit}`),
  toggleDDLMode:      (id) => api.patch(`/schema/connections/${id}/ddl-mode`),
  toggleReadonlyMode: (id) => api.patch(`/schema/connections/${id}/readonly-mode`),
  uploadSQLite: (formData) =>
    api.post('/schema/connections/upload-sqlite', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
 createEmptySQLite: (data) => api.post('/schema/connections/create-sqlite-database', data),
}

// ─── Queries ──────────────────────────────────────────────────────────────────
export const queryAPI = {
  generate:  (data) => api.post('/query/generate', data),
  execute:   (data) => api.post('/query/execute', data),
  getShared: (token) => api.get(`/query/share/${token}`),
  // DDL
  generateDDL: (data) => api.post('/query/ddl/generate', data),
  executeDDL:  (data) => api.post('/query/ddl/execute', data),
}

// ─── History ──────────────────────────────────────────────────────────────────
export const historyAPI = {
  getHistory:      (params) => api.get('/history/', { params }),
  toggleFavorite:  (id)     => api.patch(`/history/${id}/favorite`),
  deleteEntry:     (id)     => api.delete(`/history/${id}`),
}

// ─── Analytics ───────────────────────────────────────────────────────────────
export const analyticsAPI = {
  getDashboard: (days = 30) => api.get(`/analytics/dashboard?days=${days}`),
}