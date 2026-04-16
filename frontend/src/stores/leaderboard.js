import { defineStore } from 'pinia'
import { ref } from 'vue'
import { leaderboardApi } from '@/api/client'

export const useLeaderboardStore = defineStore('leaderboard', () => {
  const entries = ref([])
  const currentUserRank = ref(0)
  const loading = ref(false)

  /** @param {{ force?: boolean }} [opts] — force=true обходит блокировку при параллельном запросе (обновление после начисления) */
  async function fetch(opts = {}) {
    if (!opts.force && loading.value) return
    loading.value = true
    try {
      const res = await leaderboardApi.get()
      entries.value = res.data.entries
      currentUserRank.value = res.data.current_user_rank
    } finally {
      loading.value = false
    }
  }

  return { entries, currentUserRank, loading, fetch }
})
