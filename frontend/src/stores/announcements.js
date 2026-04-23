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
      loadError.value = typeof d === 'string' ? d : (e.message ?? 'Ошибка загрузки')
      items.value = []
      console.error('[announcements]', e.response?.status, loadError.value)
    } finally {
      loading.value = false
    }
  }

  return { items, loading, loadError, fetch }
})
