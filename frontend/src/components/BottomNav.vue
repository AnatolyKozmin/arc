<template>
  <nav class="bottom-nav">
    <!-- Sliding indicator -->
    <div class="bottom-nav__indicator" :style="indicatorStyle" />

    <RouterLink
      v-for="(tab, idx) in tabs"
      :key="tab.to"
      :to="tab.to"
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': isActive(tab.to) }"
      :ref="el => { if (el) itemRefs[idx] = el }"
    >
      <div class="bottom-nav__icon-wrap">
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
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
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
  return isAdmin ? [...baseTabs, { to: '/scan', label: 'Скан', icon: null, isScan: true }] : baseTabs
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

// ── Sliding indicator ──────────────────────────────────────────────────────
const itemRefs = ref([])
const indicatorStyle = ref({ transform: 'translateX(0px)', width: '0px' })
const ready = ref(false)

function updateIndicator() {
  const activeIdx = tabs.value.findIndex(t => isActive(t.to))
  if (activeIdx < 0) return
  const el = itemRefs.value[activeIdx]?.$el ?? itemRefs.value[activeIdx]
  if (!el) return
  const navEl = el.closest('.bottom-nav')
  if (!navEl) return
  const navRect = navEl.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  indicatorStyle.value = {
    transform: `translateX(${elRect.left - navRect.left}px)`,
    width: `${elRect.width}px`,
    opacity: ready.value ? '1' : '0',
  }
}

watch(() => route.path, async () => {
  await nextTick()
  updateIndicator()
})

watch(tabs, async () => {
  await nextTick()
  updateIndicator()
})

onMounted(async () => {
  await nextTick()
  // No transition on first render
  indicatorStyle.value = { ...indicatorStyle.value, transition: 'none' }
  updateIndicator()
  await nextTick()
  ready.value = true
  indicatorStyle.value = { ...indicatorStyle.value, transition: 'transform 0.3s cubic-bezier(0.34,1.56,0.64,1), width 0.3s cubic-bezier(0.34,1.56,0.64,1)' }
})
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

/* Sliding background pill */
.bottom-nav__indicator {
  position: absolute;
  top: 5px;
  bottom: 5px;
  border-radius: 40px;
  background: rgba(216, 216, 216, 0.6);
  pointer-events: none;
  will-change: transform, width;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1),
              width 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
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
  position: relative;
  z-index: 1;
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
  transition: color 0.2s, font-weight 0.2s;
}

.bottom-nav__item--active .bottom-nav__icon {
  color: #8127E0;
}

.bottom-nav__item--active .bottom-nav__label {
  color: #8127E0;
  font-weight: 600;
}

.bottom-nav__avatar { transition: box-shadow 0.2s; }
.bottom-nav__avatar--active { box-shadow: 0 0 0 2px #8127E0; }
</style>
