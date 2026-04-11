<template>
  <div class="app">

    <!-- Admin panel routes — render RouterView directly, no mobile shell -->
    <template v-if="isAdminRoute">
      <RouterView />
    </template>

    <!-- Mobile app -->
    <template v-else>

      <!-- Dev mode login panel -->
      <template v-if="userStore.devMode && !userStore.isAuthenticated">
        <DevPanel />
      </template>

      <!-- Не авторизованы после init (ошибка API / нет initData / не Telegram) -->
      <template v-else-if="!userStore.loading && !userStore.devMode && !userStore.isAuthenticated">
        <div class="app-loading">
          <div class="app-loading__logo"><ArcadiumIcon /></div>
          <template v-if="userStore.error">
            <p style="color:#ff3b30;font-size:13px;text-align:center;padding:0 24px">
              {{ userStore.error }}
            </p>
            <p style="color:#aaa;font-size:11px;text-align:center;padding:0 16px">
              Частая причина — неверный BOT_TOKEN на сервере или URL мини-аппа в @BotFather. В Telegram можно нажать «Обновить».
            </p>
            <button
              v-if="userStore.inTelegramWebApp"
              type="button"
              class="app-retry"
              @click="reloadApp"
            >
              Обновить
            </button>
          </template>
          <template v-else-if="!userStore.inTelegramWebApp">
            <p>Откройте приложение через Telegram</p>
            <p style="color:#aaa;font-size:12px;text-align:center;padding:0 20px">
              Мини-апп работает только внутри клиента Telegram (кнопка у бота или меню).
            </p>
          </template>
          <template v-else>
            <p>Не удалось войти</p>
            <button type="button" class="app-retry" @click="reloadApp">Обновить</button>
          </template>
        </div>
      </template>

      <!-- Registration (only after auth confirmed) -->
      <template v-else-if="userStore.isAuthenticated && !userStore.isRegistered">
        <RegisterView />
      </template>

      <!-- Main app — show immediately, nav + content appear right away -->
      <template v-else>
        <main class="app-content">
          <RouterView v-slot="{ Component }">
            <Transition name="fade" mode="out-in">
              <component :is="Component" :key="$route.name" />
            </Transition>
          </RouterView>
        </main>
        <BottomNav />

        <!-- Dev logout button -->
        <button v-if="isDev && userStore.isAuthenticated" class="dev-logout" @click="userStore.logout()" title="Dev: сменить пользователя">
          ⚙️
        </button>
      </template>

    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import BottomNav from '@/components/BottomNav.vue'
import RegisterView from '@/views/RegisterView.vue'
import ArcadiumIcon from '@/components/ArcadiumIcon.vue'
import DevPanel from '@/components/DevPanel.vue'

const userStore = useUserStore()
const route = useRoute()
const isDev = import.meta.env.DEV

const isAdminRoute = computed(() => route.path.startsWith('/admin'))

function reloadApp() {
  window.location.reload()
}

onMounted(() => {
  if (isAdminRoute.value) {
    userStore.loading = false
    return
  }
  userStore.init()
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  height: 100dvh;
  background: var(--color-bg);
}

.app-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior-y: contain;
}

.app-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--color-text-secondary);
  font-size: 15px;
}

.app-loading__logo {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  overflow: hidden;
  background: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
}

.dev-logout {
  position: fixed;
  bottom: calc(var(--nav-height) + var(--safe-bottom) + 12px);
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.12);
  border: none;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(8px);
  transition: opacity 0.2s;
}

.dev-logout:active { opacity: 0.6; }

.app-retry {
  margin-top: 8px;
  padding: 12px 28px;
  border-radius: 14px;
  border: none;
  background: var(--color-accent);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
.app-retry:active { opacity: 0.85; }

/* ── Page fade transition ─────────────────────────── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
