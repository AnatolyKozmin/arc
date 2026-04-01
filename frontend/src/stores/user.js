import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, usersApi } from '@/api/client'

const IS_DEV = import.meta.env.DEV

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('ark_token'))
  const loading = ref(false)
  const error = ref(null)
  const devMode = ref(IS_DEV && !window.Telegram?.WebApp?.initData)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isRegistered = computed(() => user.value?.is_registered ?? false)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOrganizer = computed(() => ['admin', 'organizer'].includes(user.value?.role))

  async function init() {
    // If already have a token (e.g. page reload), just re-fetch user
    if (token.value) {
      await fetchMe()
      if (user.value) return
    }

    const tg = window.Telegram?.WebApp
    if (tg?.initData) {
      tg.ready()
      tg.expand()
      try {
        loading.value = true
        const res = await authApi.telegram(tg.initData)
        token.value = res.data.access_token
        localStorage.setItem('ark_token', token.value)
        user.value = res.data.user
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }
    // If no initData and no stored token → devMode panel will show
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
