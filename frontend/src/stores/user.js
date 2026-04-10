import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, usersApi } from '@/api/client'

const IS_DEV = import.meta.env.DEV

/** Сырой initData приходит не в первый кадр — клиент Telegram заполняет строку чуть позже. */
function getInitDataRaw() {
  const s = window.Telegram?.WebApp?.initData
  return s && String(s).trim() ? String(s) : ''
}

/**
 * Ждём появления initData (обычно 0–300 ms, иногда дольше на iOS).
 * Без этого в Telegram показывается «Откройте через Telegram», хотя мини-апп открыт верно.
 */
function waitForInitData(maxMs = 2500) {
  const step = 50
  const maxAttempts = Math.ceil(maxMs / step)
  return new Promise((resolve) => {
    let i = 0
    const tick = () => {
      const raw = getInitDataRaw()
      if (raw) {
        resolve(raw)
        return
      }
      i += 1
      if (i >= maxAttempts) {
        resolve('')
        return
      }
      setTimeout(tick, step)
    }
    tick()
  })
}

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('ark_token'))
  // Start as true so we don't flash "Откройте через Telegram" on first load
  const loading = ref(true)
  const error = ref(null)
  /** В DEV: панель входа без Telegram. Не привязываем к initData при импорте модуля — он ещё пустой. */
  const devMode = ref(IS_DEV)
  /** Есть объект Telegram.WebApp (открыто внутри клиента Telegram). */
  const inTelegramWebApp = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isRegistered = computed(() => user.value?.is_registered ?? false)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOrganizer = computed(() => ['admin', 'organizer'].includes(user.value?.role))

  async function init() {
    loading.value = true
    error.value = null
    const tg = window.Telegram?.WebApp
    inTelegramWebApp.value = !!tg

    try {
      tg?.ready()
      tg?.expand()

      // Уже есть сессия (перезагрузка страницы)
      if (token.value) {
        await fetchMe()
        if (user.value) {
          devMode.value = false
          return
        }
      }

      // Ждём initData — критично для корректной работы в Telegram
      const initData = await waitForInitData()
      inTelegramWebApp.value = !!window.Telegram?.WebApp

      if (initData) {
        devMode.value = false
        const res = await authApi.telegram(initData)
        token.value = res.data.access_token
        localStorage.setItem('ark_token', token.value)
        user.value = res.data.user
        return
      }

      // Нет initData после ожидания
      if (IS_DEV && !inTelegramWebApp.value) {
        // Локальная разработка в браузере без Telegram
        devMode.value = true
        return
      }

      if (inTelegramWebApp.value) {
        // Внутри Telegram, но initData так и не пришёл
        error.value =
          'Не удалось получить данные входа Telegram. Закройте мини-апп и откройте снова через кнопку в боте или меню (не как обычную ссылку в браузере).'
        devMode.value = false
        return
      }

      // Не Telegram и не dev
      devMode.value = false
    } catch (e) {
      const detail = e.response?.data?.detail ?? e.message ?? 'Ошибка авторизации'
      error.value = detail
      devMode.value = false
      console.error('[auth]', detail, e)
    } finally {
      loading.value = false
    }
  }

  async function devLogin(params) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.dev(params)
      token.value = res.data.access_token
      localStorage.setItem('ark_token', token.value)
      user.value = res.data.user
      devMode.value = false
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('ark_token')
    devMode.value = IS_DEV
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await usersApi.me()
      user.value = res.data
    } catch {
      token.value = null
      localStorage.removeItem('ark_token')
    }
  }

  async function register(data) {
    const res = await usersApi.register(data)
    user.value = res.data
  }

  async function setCharacter(characterId) {
    const res = await usersApi.setCharacter(characterId)
    user.value = res.data
    return res.data
  }

  function getInitials() {
    if (!user.value) return 'TG'
    const first = user.value.first_name?.[0] ?? ''
    const last = user.value.last_name?.[0] ?? ''
    return (first + last).toUpperCase() || 'TG'
  }

  return {
    user,
    token,
    loading,
    error,
    devMode,
    inTelegramWebApp,
    isAuthenticated,
    isRegistered,
    isAdmin,
    isOrganizer,
    init,
    fetchMe,
    register,
    setCharacter,
    getInitials,
    devLogin,
    logout,
  }
})
