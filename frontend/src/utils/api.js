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
          const { data } = await axios.post('/api/auth/refresh', null, {
            params: { refresh_token: refresh },
          })

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

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  updateMode: (mode) => api.patch(`/auth/me/mode?mode=${mode}`),
}

export const schemaAPI = {
  getConnections: () => api.get('/schema/connections'),
  createConnection: (data) => api.post('/schema/connections', data),
  refreshSchema: (id) => api.post(`/schema/connections/${id}/refresh-schema`),
  getSchema: (id) => api.get(`/schema/connections/${id}/schema`),
  previewTable: (connectionId, tableName, limit = 10) =>
    api.get(`/schema/connections/${connectionId}/tables/${tableName}/preview`, {
      params: { limit },
    }),
  deleteConnection: (id) => api.delete(`/schema/connections/${id}`),
  connectDemo: (demoName) => api.post(`/schema/demo/${demoName}/connect`),
  uploadSQLite: (formData) =>
  api.post('/schema/connections/upload-sqlite', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
}

export const queryAPI = {
  generate: (data) => api.post('/query/generate', data),
  execute: (data) => api.post('/query/execute', data),
  getShared: (token) => api.get(`/query/share/${token}`),
}

export const historyAPI = {
  getHistory: (params) => api.get('/history/', { params }),
  toggleFavorite: (id) => api.patch(`/history/${id}/favorite`),
  deleteEntry: (id) => api.delete(`/history/${id}`),
}

export const analyticsAPI = {
  getDashboard: (days = 30) => api.get(`/analytics/dashboard?days=${days}`),
}