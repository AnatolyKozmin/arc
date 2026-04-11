import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, usersApi } from '@/api/client'
import { getInitDataRaw, ARK_TG_INIT_STORAGE_KEY } from '@/utils/tgInitData'

const IS_DEV = import.meta.env.DEV

/**
 * Ждём появления initData (на iOS/WebView иногда 1–5+ с).
 * На каждом шаге снова читаем URL и WebApp — не только sessionStorage с первого кадра.
 */
function waitForInitData(maxMs = 10000) {
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

/** Один параллельный init (Strict Mode / повторный mount не должны гонять два init). */
let initInFlight = null

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
    if (initInFlight) return initInFlight

    initInFlight = (async () => {
      loading.value = true
      error.value = null
      const tg = window.Telegram?.WebApp
      inTelegramWebApp.value = !!tg

      try {
        // ready/expand — в src/telegram/bootstrapWebApp.js при старте

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
          try {
            sessionStorage.removeItem(ARK_TG_INIT_STORAGE_KEY)
          } catch (_) {}
          return
        }

        // Нет initData после ожидания
        if (IS_DEV && !inTelegramWebApp.value) {
          devMode.value = true
          return
        }

        if (inTelegramWebApp.value) {
          error.value =
            'Не удалось получить данные входа Telegram. Откройте мини-апп через кнопку меню чата (слева от поля ввода, «🎮 Аркадиум») или нажмите «🎮 Аркадиум» на клавиатуре и затем «Открыть Аркадиум». Не открывайте сайт как обычную ссылку в браузере.'
          devMode.value = false
          return
        }

        devMode.value = false
      } catch (e) {
        const detail = e.response?.data?.detail ?? e.message ?? 'Ошибка авторизации'
        error.value = detail
        devMode.value = false
        console.error('[auth]', detail, e)
      } finally {
        loading.value = false
      }
    })()

    return initInFlight.finally(() => {
      initInFlight = null
    })
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
