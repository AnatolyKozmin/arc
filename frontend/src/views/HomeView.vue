<template>
  <div class="home">
    <AppHeader
      :balance="userStore.user?.balance ?? 0"
      :photo-url="userStore.user?.photo_url"
      :initials="userStore.getInitials()"
    />

    <!-- Объявления -->
    <section class="home__section">
      <div class="section-header">
        <span class="section-header__title">Объявления</span>
      </div>
      <div v-if="announcementsStore.loading" class="home__skeleton-banner skeleton" />
      <AnnouncementSlider
        v-else-if="announcementsStore.items.length"
        :items="announcementsStore.items"
      />
      <div v-else class="home__empty">Нет объявлений</div>
    </section>

    <!-- Магазин -->
    <section class="home__section">
      <div class="section-header">
        <span class="section-header__title">Магазин</span>
        <RouterLink to="/shop" class="section-header__action">Смотреть всё</RouterLink>
      </div>

      <div v-if="shopStore.loading" class="home__scroll-row">
        <div v-for="i in 3" :key="i" class="home__skeleton-card skeleton" />
      </div>
      <div v-else-if="shopStore.featured.length" class="home__scroll-row">
        <div
          v-for="product in shopStore.featured"
          :key="product.id"
          class="home__card-wrap"
        >
          <ProductCard :product="product" @click="openProduct" />
        </div>
      </div>
      <p v-else class="home__empty">Товары появятся скоро</p>
    </section>

    <ProductModal :product="selectedProduct" @close="selectedProduct = null" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAnnouncementsStore } from '@/stores/announcements'
import { useShopStore } from '@/stores/shop'
import AppHeader from '@/components/AppHeader.vue'
import AnnouncementSlider from '@/components/AnnouncementSlider.vue'
import ProductCard from '@/components/ProductCard.vue'
import ProductModal from '@/components/ProductModal.vue'

const userStore = useUserStore()
const announcementsStore = useAnnouncementsStore()
const shopStore = useShopStore()
const selectedProduct = ref(null)

function openProduct(product) {
  selectedProduct.value = product
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
}

onMounted(() => {
  announcementsStore.fetch()
  shopStore.fetchAll()
})
</script>

<style scoped>
.home {
  min-height: 100%;
  background: #fff;
  padding-top: var(--safe-top);
  padding-bottom: var(--nav-height);
}

.home__section {
  margin-top: 4px;
}

/* Horizontal scroll strip for shop preview cards */
.home__scroll-row {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 0 16px 8px;
  scroll-snap-type: x mandatory;
}

.home__card-wrap {
  width: 200px;
  flex-shrink: 0;
  scroll-snap-align: start;
}

.home__skeleton-banner {
  height: 0;
  padding-bottom: calc(100% * 236 / 360);
  border-radius: 16px;
  margin: 0 16px;
}

.home__skeleton-card {
  width: 200px;
  height: 268px;
  flex-shrink: 0;
  border-radius: 16px;
}

.home__empty {
  padding: 16px 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
}
</style>
