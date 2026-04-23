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

/** Текст ошибки API (string detail или Pydantic / массив). */
export function apiErrorMessage(error, fallback = 'Ошибка запроса') {
  const d = error?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'string' ? x : x?.msg || JSON.stringify(x)))
      .filter(Boolean)
      .join(' ')
  }
  if (d && typeof d === 'object' && d.msg) return d.msg
  return error?.message || fallback
}

// ── Auth ──────────────────────────────────────────────────────────────────────
// fetch: не трогает baseURL/axios; при обрезанном пути в прокси бэкенд принимает POST /api/ с init_data.
async function postJson(path, data) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  let resData
  try {
    resData = await r.json()
  } catch {
    resData = {}
  }
  if (!r.ok) {
    const e = new Error('Request failed')
    e.response = { status: r.status, data: resData }
    throw e
  }
  return { data: resData }
}

export const authApi = {
  telegram: (initData) => postJson('/api/auth/telegram', { init_data: initData }),
  dev: (data) => postJson('/api/auth/dev', data),
}

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  me: () => client.get('/users/me'),
  // POST: надёжнее PUT за прокси/мини-апп; путь от корня, без merge с baseURL /api
  register: (data) =>
    client.request({
      method: 'post',
      baseURL: '',
      url: '/api/users/me/register',
      data,
    }),
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
  purchase: (id) => client.post(`/products/${id}/purchase`),
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
