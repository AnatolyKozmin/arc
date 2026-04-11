import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

/** Один logout на пачку параллельных 401 — меньше дерганий Pinia/шаблона. */
let logout401Scheduled = false

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('ark_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const url = error.config?.url ?? ''
    const isAuthEndpoint = url.includes('/auth/')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('ark_token')
      if (!logout401Scheduled) {
        logout401Scheduled = true
        queueMicrotask(async () => {
          logout401Scheduled = false
          try {
            const { useUserStore } = await import('@/stores/user')
            useUserStore().logout()
          } catch (_) {}
        })
      }
    }
    return Promise.reject(error)
  }
)

export default client

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  telegram: (initData) => client.post('/auth/telegram', { init_data: initData }),
  dev: (data) => client.post('/auth/dev', data),
}

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  me: () => client.get('/users/me'),
  register: (data) => client.put('/users/me/register', data),
  setCharacter: (character_id) => client.put('/users/me/character', { character_id }),
  adjustBalance: (userId, amount, reason) =>
    client.post(`/users/${userId}/balance`, { amount, reason }),
  list: () => client.get('/users'),
}

// ── Announcements ─────────────────────────────────────────────────────────────
export const announcementsApi = {
  list: () => client.get('/announcements'),
  create: (data) => client.post('/announcements', data),
  update: (id, data) => client.put(`/announcements/${id}`, data),
  delete: (id) => client.delete(`/announcements/${id}`),
}

// ── Products ──────────────────────────────────────────────────────────────────
export const productsApi = {
  list: (featuredOnly = false) =>
    client.get('/products', { params: { featured_only: featuredOnly } }),
  get: (id) => client.get(`/products/${id}`),
  create: (data) => client.post('/products', data),
  update: (id, data) => client.put(`/products/${id}`, data),
  delete: (id) => client.delete(`/products/${id}`),
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
export const leaderboardApi = {
  get: () => client.get('/leaderboard'),
}

// ── Achievements ──────────────────────────────────────────────────────────────
export const achievementsApi = {
  list: () => client.get('/achievements'),
  mine: () => client.get('/achievements/me'),
  claim: (id) => client.post(`/achievements/me/${id}/claim`),
  grant: (userId, achievementId) =>
    client.post(`/achievements/${userId}/grant/${achievementId}`),
}

// ── Transactions ──────────────────────────────────────────────────────────────
export const transactionsApi = {
  mine: (skip = 0, limit = 50) =>
    client.get('/transactions/me', { params: { skip, limit } }),
}
