import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

// Use relative URL so requests go through Vite proxy (avoids CORS issues in dev)
const BASE = '/api'

const http = axios.create({ baseURL: BASE })

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('panel_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export const useAdminStore = defineStore('admin', () => {
  const token = ref(localStorage.getItem('panel_token') || null)
  const loading = ref(false)
  const error = ref(null)

  const isLoggedIn = () => !!token.value

  async function login(username, password) {
    error.value = null
    loading.value = true
    try {
      const res = await http.post('/panel/login', { username, password })
      token.value = res.data.access_token
      localStorage.setItem('panel_token', token.value)
      return true
    } catch (e) {
      const d = e.response?.data?.detail
      if (d == null && !e.response) {
        error.value = 'Нет ответа от API (сеть, 502 или CORS). Проверь DOMAIN и CORS_ORIGINS в .env, пересоздай backend.'
      } else {
        error.value = typeof d === 'string' ? d : 'Ошибка входа'
      }
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    localStorage.removeItem('panel_token')
  }

  // ── API helpers ──────────────────────────────────────────────────────────────

  async function getStats() {
    const r = await http.get('/panel/stats')
    return r.data
  }

  // Users
  async function getUsers(search = '', skip = 0, limit = 50) {
    const r = await http.get('/panel/users', { params: { search: search || undefined, skip, limit } })
    return r.data
  }

  async function updateBalance(userId, amount, reason) {
    const r = await http.patch(`/panel/users/${userId}/balance`, { amount, reason })
    return r.data
  }

  /** Создать или обновить участника по telegram_id (как бот при /start). */
  async function ensureUser(payload) {
    const r = await http.post('/panel/users/ensure', payload)
    return r.data
  }

  /** Резолв @username через Telegram Bot API и upsert (нужен BOT_TOKEN на бэкенде). */
  async function ensureUserByUsername(payload) {
    const r = await http.post('/panel/users/ensure-by-username', payload)
    return r.data
  }

  // Announcements
  async function getAnnouncements() {
    const r = await http.get('/panel/announcements')
    return r.data
  }

  async function createAnnouncement(data) {
    const r = await http.post('/panel/announcements', data)
    return r.data
  }

  async function updateAnnouncement(id, data) {
    const r = await http.put(`/panel/announcements/${id}`, data)
    return r.data
  }

  async function deleteAnnouncement(id) {
    await http.delete(`/panel/announcements/${id}`)
  }

  // Products
  async function getProducts() {
    const r = await http.get('/panel/products')
    return r.data
  }

  async function createProduct(data) {
    const r = await http.post('/panel/products', data)
    return r.data
  }

  async function updateProduct(id, data) {
    const r = await http.put(`/panel/products/${id}`, data)
    return r.data
  }

  async function deleteProduct(id) {
    await http.delete(`/panel/products/${id}`)
  }

  /** Загрузка картинки (multipart); возвращает URL вида /api/uploads/... */
  async function uploadImage(file) {
    const fd = new FormData()
    fd.append('file', file)
    const r = await http.post('/panel/upload', fd)
    return r.data.url
  }

  // Achievements
  async function getAchievements() {
    const r = await http.get('/panel/achievements')
    return r.data
  }

  async function createAchievement(data) {
    const r = await http.post('/panel/achievements', data)
    return r.data
  }

  async function updateAchievement(id, data) {
    const r = await http.put(`/panel/achievements/${id}`, data)
    return r.data
  }

  async function deleteAchievement(id) {
    await http.delete(`/panel/achievements/${id}`)
  }

  async function assignAchievement(userId, achievementId) {
    await http.post('/panel/achievements/assign', { user_id: userId, achievement_id: achievementId })
  }

  /** Скачать Excel: только зарегистрированные на мероприятие (анкета, is_registered). */
  async function exportUsersXlsx() {
    const r = await http.get('/panel/users/export', { responseType: 'blob' })
    const cd = r.headers['content-disposition'] || r.headers['Content-Disposition']
    let filename = 'arkadium-meropriyatie.xlsx'
    if (cd) {
      const m = cd.match(/filename\*?=(?:UTF-8'')?["']?([^";\n]+)["']?/i) || cd.match(/filename="([^"]+)"/)
      if (m) {
        filename = decodeURIComponent(m[1].trim())
      }
    }
    const url = window.URL.createObjectURL(new Blob([r.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return {
    token, loading, error, isLoggedIn, http,
    login, logout,
    getStats,
    getUsers, updateBalance, ensureUser, ensureUserByUsername, exportUsersXlsx,
    getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement,
    getProducts, createProduct, updateProduct, deleteProduct, uploadImage,
    getAchievements, createAchievement, updateAchievement, deleteAchievement, assignAchievement,
  }
})
