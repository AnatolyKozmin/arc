<template>
  <div class="dashboard">
    <h1 class="page-title">Дашборд</h1>

    <div v-if="loading" class="stats-grid">
      <div v-for="i in 5" :key="i" class="stat-card stat-card--skeleton" />
    </div>

    <div v-else class="stats-grid">
      <div class="stat-card">
        <span class="stat-card__icon">👥</span>
        <div>
          <p class="stat-card__value">{{ stats.total_users }}</p>
          <p class="stat-card__label">Пользователей</p>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-card__icon">✅</span>
        <div>
          <p class="stat-card__value">{{ stats.registered_users }}</p>
          <p class="stat-card__label">Зарегистрировано</p>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-card__icon">🛍️</span>
        <div>
          <p class="stat-card__value">{{ stats.total_products }}</p>
          <p class="stat-card__label">Товаров</p>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-card__icon">📣</span>
        <div>
          <p class="stat-card__value">{{ stats.total_announcements }}</p>
          <p class="stat-card__label">Объявлений</p>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-card__icon">🏆</span>
        <div>
          <p class="stat-card__value">{{ stats.total_achievements }}</p>
          <p class="stat-card__label">Достижений</p>
        </div>
      </div>
    </div>

    <div class="quick-links">
      <h2 class="section-title">Быстрые действия</h2>
      <div class="quick-grid">
        <RouterLink to="/admin/announcements" class="quick-card">
          <span>📣</span>
          <p>Добавить объявление</p>
        </RouterLink>
        <RouterLink to="/admin/products" class="quick-card">
          <span>🎁</span>
          <p>Добавить товар</p>
        </RouterLink>
        <RouterLink to="/admin/users" class="quick-card">
          <span>💰</span>
          <p>Начислить аркоины</p>
        </RouterLink>
        <RouterLink to="/admin/achievements" class="quick-card">
          <span>🏅</span>
          <p>Выдать достижение</p>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()
const loading = ref(true)
const stats = ref({ total_users: 0, registered_users: 0, total_products: 0, total_announcements: 0, total_achievements: 0 })

onMounted(async () => {
  try { stats.value = await store.getStats() }
  finally { loading.value = false }
})
</script>

<style scoped>
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #000;
  margin-bottom: 24px;
  letter-spacing: -0.4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-card--skeleton {
  height: 82px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e4e4e4 50%, #f0f0f0 75%);
  background-size: 400px 100%;
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  from { background-position: -400px 0; }
  to { background-position: 400px 0; }
}

.stat-card__icon { font-size: 28px; }
.stat-card__value { font-size: 26px; font-weight: 700; color: #000; letter-spacing: -0.5px; }
.stat-card__label { font-size: 12px; color: #888; margin-top: 2px; }

.section-title { font-size: 16px; font-weight: 600; color: #333; margin-bottom: 16px; }

.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.quick-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: transform 0.15s, box-shadow 0.15s;
  cursor: pointer;
  border: 1.5px solid transparent;
}

.quick-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
  border-color: rgba(129,39,224,0.2);
}

.quick-card span { font-size: 32px; }
.quick-card p { font-size: 13px; font-weight: 600; color: #333; text-align: center; }
</style>
