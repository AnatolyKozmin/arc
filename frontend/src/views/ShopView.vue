<template>
  <div class="shop">
    <AppHeader
      :balance="userStore.user?.balance ?? 0"
      :photo-url="userStore.user?.photo_url"
      :initials="userStore.getInitials()"
    />

    <div class="section-header">
      <span class="section-header__title">Магазин</span>
    </div>

    <div v-if="shopStore.loading" class="shop__grid">
      <div v-for="i in 6" :key="i" class="skeleton shop__skeleton-card" />
    </div>

    <div v-else-if="shopStore.products.length" class="shop__grid">
      <ProductCard
        v-for="product in shopStore.products"
        :key="product.id"
        :product="product"
        @click="openProduct"
      />
    </div>

    <div v-else class="shop__empty">
      <span>🎁</span>
      <p>Товары появятся скоро</p>
    </div>

    <ProductModal
      :product="selectedProduct"
      @close="selectedProduct = null"
      @purchased="onPurchased"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useShopStore } from '@/stores/shop'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/AppHeader.vue'
import ProductCard from '@/components/ProductCard.vue'
import ProductModal from '@/components/ProductModal.vue'

const shopStore = useShopStore()
const userStore = useUserStore()
const selectedProduct = ref(null)

function openProduct(product) {
  selectedProduct.value = product
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
}

function onPurchased({ product }) {
  shopStore.applyProductUpdate(product)
  if (selectedProduct.value?.id === product.id) {
    selectedProduct.value = { ...selectedProduct.value, ...product }
  }
}

onMounted(() => shopStore.fetchAll())
</script>

<style scoped>
.shop {
  min-height: 100%;
  background: #fff;
  padding-top: var(--safe-top);
  padding-bottom: var(--nav-height);
}

.shop__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 0 16px 8px;
}

.shop__skeleton-card {
  height: 220px;
  border-radius: 16px;
}

.shop__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 16px;
  color: var(--color-text-secondary);
}

.shop__empty span { font-size: 48px; }
.shop__empty p { font-size: 15px; }
</style>
