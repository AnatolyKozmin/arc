import { defineStore } from 'pinia'
import { ref } from 'vue'
import { productsApi } from '@/api/client'

export const useShopStore = defineStore('shop', () => {
  const products = ref([])
  const featured = ref([])
  const loading = ref(false)
  const loadError = ref(null)
  const selected = ref(null)

  async function fetchAll() {
    if (loading.value) return
    loading.value = true
    loadError.value = null
    try {
      const res = await productsApi.list()
      products.value = res.data
      featured.value = res.data.filter((p) => p.is_featured)
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
      products.value = []
      featured.value = []
      console.error('[shop]', e.response?.status, loadError.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchProduct(id) {
    const res = await productsApi.get(id)
    selected.value = res.data
    return res.data
  }

  /** После покупки — подставить актуальный остаток без полной перезагрузки списка. */
  function applyProductUpdate(p) {
    const i = products.value.findIndex((x) => x.id === p.id)
    if (i >= 0) products.value[i] = { ...products.value[i], ...p }
    const j = featured.value.findIndex((x) => x.id === p.id)
    if (j >= 0) featured.value[j] = { ...featured.value[j], ...p }
  }

  return { products, featured, loading, loadError, selected, fetchAll, fetchProduct, applyProductUpdate }
})
