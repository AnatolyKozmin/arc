import { defineStore } from 'pinia'
import { ref } from 'vue'
import { announcementsApi } from '@/api/client'

export const useAnnouncementsStore = defineStore('announcements', () => {
  const items = ref([])
  const loading = ref(false)

  async function fetch() {
    if (loading.value) return
    loading.value = true
    try {
      const res = await announcementsApi.list()
      items.value = res.data
    } finally {
      loading.value = false
    }
  }

  return { items, loading, fetch }
})
