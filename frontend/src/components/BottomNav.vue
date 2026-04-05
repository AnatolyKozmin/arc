<template>
  <nav class="bottom-nav">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.to"
      :to="tab.to"
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': isActive(tab.to) }"
    >
      <div class="bottom-nav__icon-wrap">
        <!-- Profile tab: show user avatar -->
        <template v-if="tab.to === '/profile'">
          <UserAvatar
            :photo-url="userStore.user?.photo_url"
            :initials="userStore.getInitials()"
            :size="26"
            class="bottom-nav__avatar"
            :class="{ 'bottom-nav__avatar--active': isActive('/profile') }"
          />
        </template>
        <template v-else-if="tab.isScan">
          <svg class="bottom-nav__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <path d="M14 14h2v2h-2zM18 14h3M14 18h2M18 18h3v3M21 14v2"/>
          </svg>
        </template>
        <template v-else>
          <component :is="tab.icon" class="bottom-nav__icon" />
        </template>
      </div>
      <span class="bottom-nav__label">{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { RouterLink } from 'vue-router'
import { useUserStore } from '@/stores/user'
import IconHome from '@/components/icons/IconHome.vue'
import IconTop from '@/components/icons/IconTop.vue'
import IconShop from '@/components/icons/IconShop.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const route = useRoute()
const userStore = useUserStore()

const baseTabs = [
  { to: '/', label: 'Главная', icon: IconHome },
  { to: '/top', label: 'Топ', icon: IconTop },
  { to: '/shop', label: 'Магазин', icon: IconShop },
  { to: '/profile', label: 'Профиль', icon: null },
]

const tabs = computed(() => {
  const isAdmin = userStore.user?.role === 'admin' || userStore.user?.role === 'organizer'
  if (isAdmin) {
    return [...baseTabs, { to: '/scan', label: 'Скан', icon: null, isScan: true }]
  }
  return baseTabs
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: calc(12px + var(--safe-bottom));
  left: 16px;
  right: 16px;
  background: #ffffff;
  border-radius: 40px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: stretch;
  padding: 5px;
  z-index: 100;
}

.bottom-nav__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: #6E6E71;
  padding: 6px 4px;
  border-radius: 40px;
  transition: background 0.2s ease;
}

.bottom-nav__icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.bottom-nav__icon {
  width: 26px;
  height: 26px;
  transition: color 0.2s;
}

.bottom-nav__label {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1.2;
  color: rgba(84, 84, 88, 0.85);
  transition: color 0.2s;
}

.bottom-nav__item--active {
  background: rgba(216, 216, 216, 0.6);
}

.bottom-nav__item--active .bottom-nav__icon {
  color: #8127E0;
}

.bottom-nav__item--active .bottom-nav__label {
  color: #8127E0;
}

/* Avatar in profile tab */
.bottom-nav__avatar {
  transition: box-shadow 0.2s;
}

.bottom-nav__avatar--active {
  box-shadow: 0 0 0 2px #8127E0;
}
</style>
