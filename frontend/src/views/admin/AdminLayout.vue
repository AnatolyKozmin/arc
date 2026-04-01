<template>
  <div class="admin">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar__brand">
        <span class="sidebar__emoji">🎮</span>
        <span class="sidebar__name">Аркадиум</span>
      </div>

      <nav class="sidebar__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="sidebar__link"
          :class="{ 'sidebar__link--active': isActive(item.to) }"
        >
          <span class="sidebar__link-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <button class="sidebar__logout" @click="handleLogout">
        <span>🚪</span> Выйти
      </button>
    </aside>

    <!-- Content -->
    <main class="admin__content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRoute, useRouter, RouterLink, RouterView } from 'vue-router'
import { useAdminStore } from '@/stores/admin'

const route = useRoute()
const router = useRouter()
const store = useAdminStore()

const navItems = [
  { to: '/admin', icon: '📊', label: 'Дашборд' },
  { to: '/admin/users', icon: '👥', label: 'Участники' },
  { to: '/admin/announcements', icon: '📣', label: 'Объявления' },
  { to: '/admin/products', icon: '🛍️', label: 'Товары' },
  { to: '/admin/achievements', icon: '🏆', label: 'Достижения' },
]

function isActive(to) {
  if (to === '/admin') return route.path === '/admin'
  return route.path.startsWith(to)
}

function handleLogout() {
  store.logout()
  router.push('/admin/login')
}
</script>

<style scoped>
.admin {
  display: flex;
  min-height: 100vh;
  background: #f5f5f7;
}

/* ── Sidebar ──────────────────────────────────────── */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  padding: 0 0 24px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.sidebar__emoji { font-size: 24px; }

.sidebar__name {
  font-size: 17px;
  font-weight: 700;
  color: #000;
  letter-spacing: -0.3px;
}

.sidebar__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 10px;
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  color: #444;
  transition: background 0.15s, color 0.15s;
}

.sidebar__link:hover { background: #f5f5f7; }

.sidebar__link--active {
  background: rgba(129, 39, 224, 0.1);
  color: #8127E0;
  font-weight: 600;
}

.sidebar__link-icon { font-size: 18px; width: 22px; text-align: center; }

.sidebar__logout {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 10px;
  padding: 10px 12px;
  border: none;
  background: none;
  color: #999;
  font-size: 14px;
  cursor: pointer;
  border-radius: 10px;
  transition: background 0.15s, color 0.15s;
}

.sidebar__logout:hover { background: #fff0f0; color: #ff3b30; }

/* ── Content ──────────────────────────────────────── */
.admin__content {
  flex: 1;
  overflow: auto;
  padding: 32px;
  min-width: 0;
}

@media (max-width: 700px) {
  .admin { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: static; flex-direction: row; flex-wrap: wrap; padding: 12px; }
  .sidebar__brand { border: none; padding: 0; margin: 0 12px 0 0; }
  .sidebar__nav { flex-direction: row; padding: 0; }
  .sidebar__link { padding: 8px 10px; font-size: 12px; }
  .sidebar__logout { margin: 0; padding: 8px 10px; }
  .admin__content { padding: 16px; }
}
</style>
