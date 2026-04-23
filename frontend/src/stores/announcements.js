import { defineStore } from 'pinia'
import { ref } from 'vue'
import { announcementsApi } from '@/api/client'

export const useAnnouncementsStore = defineStore('announcements', () => {
  const items = ref([])
  const loading = ref(false)
  const loadError = ref(null)

  async function fetch() {
    if (loading.value) return
    loading.value = true
    loadError.value = null
    try {
      const res = await announcementsApi.list()
      items.value = res.data
    } catch (e) {
      const d = e.response?.data?.detail
      const base = e.config?.baseURL ?? ''
      let qs = ''
      try {
        if (e.config?.params && typeof e.config.params === 'object') {
          qs = '?' + new URLSearchParams(e.config.params).toString()
        }
      } catch (_) {}
      const url = (e.config?.url ?? '') + qs
      const req = `${e.config?.method?.toUpperCase() ?? '?'} ${base}${url}`.trim()
      let msg = typeof d === 'string' ? d : (e.message ?? 'Ошибка загрузки')
      if (e.response?.status === 405 || msg === 'Method Not Allowed') {
        msg += ` (${req}). Nginx: location /api/ → proxy_pass http://бэк:8000$request_uri без /api/ в URL upstream.`
      } else if (req.length > 10) {
        msg += ` (${req})`
      }
      loadError.value = msg
      items.value = []
      console.error('[announcements]', e.response?.status, loadError.value)
    } finally {
      loading.value = false
    }
  }

  return { items, loading, loadError, fetch }
})
