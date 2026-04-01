import { defineStore } from 'pinia'
import { ref } from 'vue'
import { productsApi } from '@/api/client'

export const useShopStore = defineStore('shop', () => {
  const products = ref([])
  const featured = ref([])
  const loading = ref(false)
  const selected = ref(null)

  async function fetchAll() {
    if (loading.value) return
    loading.value = true
    try {
      const res = await productsApi.list()
      products.value = res.data
      featured.value = res.data.filter((p) => p.is_featured)
    } finally {
      loading.value = false
    }
  }

  async function fetchProduct(id) {
    const res = await productsApi.get(id)
    selected.value = res.data
    return res.data
  }

  return { products, featured, loading, selected, fetchAll, fetchProduct }
})
