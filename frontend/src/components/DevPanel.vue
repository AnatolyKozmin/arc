<template>
  <div class="dev-panel">
    <div class="dev-panel__card">
      <div class="dev-panel__header">
        <div class="dev-panel__badge">DEV MODE</div>
        <div class="dev-panel__logo">
          <ArcadiumIcon />
        </div>
        <h1 class="dev-panel__title">Аркадиум</h1>
        <p class="dev-panel__subtitle">Войти как тестовый пользователь</p>
      </div>

      <div class="dev-panel__presets">
        <button
          v-for="p in presets"
          :key="p.telegram_id"
          class="preset-btn"
          :class="`preset-btn--${p.role}`"
          :disabled="store.loading"
          @click="loginAs(p)"
        >
          <span class="preset-btn__emoji">{{ p.emoji }}</span>
          <div class="preset-btn__info">
            <span class="preset-btn__name">{{ p.first_name }} {{ p.last_name }}</span>
            <span class="preset-btn__role">{{ roleLabel(p.role) }} · ID {{ p.telegram_id }}</span>
          </div>
          <span class="preset-btn__arrow">→</span>
        </button>
      </div>

      <div class="dev-panel__divider">
        <span>или введите вручную</span>
      </div>

      <form class="dev-panel__form" @submit.prevent="loginCustom">
        <div class="dev-panel__row">
          <div class="dev-panel__field">
            <label>Telegram ID</label>
            <input v-model.number="custom.telegram_id" type="number" placeholder="123456789" required />
          </div>
          <div class="dev-panel__field">
            <label>Роль</label>
            <select v-model="custom.role">
              <option value="user">User</option>
              <option value="organizer">Organizer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        <div class="dev-panel__row">
          <div class="dev-panel__field">
            <label>Имя</label>
            <input v-model="custom.first_name" type="text" placeholder="Иван" required />
          </div>
          <div class="dev-panel__field">
            <label>Фамилия</label>
            <input v-model="custom.last_name" type="text" placeholder="Иванов" />
          </div>
        </div>
        <div class="dev-panel__field">
          <label>Username</label>
          <input v-model="custom.username" type="text" placeholder="@ivan" />
        </div>

        <button class="dev-panel__submit" type="submit" :disabled="store.loading">
          {{ store.loading ? 'Входим...' : 'Войти' }}
        </button>
      </form>

      <p v-if="store.error" class="dev-panel__error">{{ store.error }}</p>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useUserStore } from '@/stores/user'
import ArcadiumIcon from '@/components/ArcadiumIcon.vue'

const store = useUserStore()

const presets = [
  { telegram_id: 1001, first_name: 'Александра', last_name: 'Жаркова', username: 'sasha_org', role: 'admin', emoji: '👑' },
  { telegram_id: 1002, first_name: 'Ольга', last_name: 'Сусина', username: 'olga_org', role: 'organizer', emoji: '🎯' },
  { telegram_id: 1003, first_name: 'Иван', last_name: 'Студент', username: 'ivan_s', role: 'user', emoji: '🎮' },
  { telegram_id: 1004, first_name: 'Мария', last_name: 'Геймер', username: 'masha_g', role: 'user', emoji: '🕹️' },
]

const custom = reactive({
  telegram_id: 9999,
  first_name: 'Dev',
  last_name: 'User',
  username: 'devuser',
  role: 'user',
})

function loginAs(preset) {
  store.devLogin({ ...preset })
}

function loginCustom() {
  store.devLogin({ ...custom })
}

function roleLabel(role) {
  return { user: 'Участник', organizer: 'Организатор', admin: 'Администратор' }[role] ?? role
}
</script>

<style scoped>
.dev-panel {
  min-height: 100dvh;
  background: linear-gradient(160deg, #1a0033 0%, #0d001a 100%);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px 16px 40px;
  overflow-y: auto;
}

.dev-panel__card {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dev-panel__header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding-top: 8px;
}

.dev-panel__badge {
  background: rgba(255, 149, 0, 0.2);
  color: #FF9500;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid rgba(255, 149, 0, 0.3);
}

.dev-panel__logo {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  overflow: hidden;
}

.dev-panel__title {
  font-size: 26px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.5px;
  margin: 0;
}

.dev-panel__subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

/* Presets */
.dev-panel__presets {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: none;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.07);
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-align: left;
  width: 100%;
}

.preset-btn:active { transform: scale(0.98); }
.preset-btn:disabled { opacity: 0.5; cursor: default; }

.preset-btn--admin { border-color: rgba(255, 215, 0, 0.25); background: rgba(255, 215, 0, 0.07); }
.preset-btn--organizer { border-color: rgba(129, 39, 224, 0.3); background: rgba(129, 39, 224, 0.1); }
.preset-btn--user { border-color: rgba(255, 255, 255, 0.1); }

.preset-btn__emoji { font-size: 28px; flex-shrink: 0; }

.preset-btn__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.preset-btn__name {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

.preset-btn__role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.preset-btn--admin .preset-btn__role { color: rgba(255, 215, 0, 0.7); }
.preset-btn--organizer .preset-btn__role { color: rgba(167, 100, 255, 0.8); }

.preset-btn__arrow {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.3);
}

/* Divider */
.dev-panel__divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.25);
  font-size: 12px;
  font-weight: 500;
}

.dev-panel__divider::before,
.dev-panel__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
}

/* Manual form */
.dev-panel__form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dev-panel__row {
  display: flex;
  gap: 10px;
}

.dev-panel__field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.dev-panel__field label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding-left: 2px;
}

.dev-panel__field input,
.dev-panel__field select {
  width: 100%;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #ffffff;
  font-size: 15px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
  appearance: none;
  -webkit-appearance: none;
}

.dev-panel__field input:focus,
.dev-panel__field select:focus {
  border-color: rgba(129, 39, 224, 0.6);
}

.dev-panel__field input::placeholder { color: rgba(255,255,255,0.2); }

.dev-panel__field select option { background: #1a0033; color: white; }

.dev-panel__submit {
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #8127E0, #5a1ba0);
  color: white;
  font-size: 16px;
  font-weight: 700;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  margin-top: 4px;
  transition: opacity 0.15s, transform 0.1s;
}

.dev-panel__submit:active { transform: scale(0.98); }
.dev-panel__submit:disabled { opacity: 0.5; cursor: default; }

.dev-panel__error {
  text-align: center;
  color: #FF3B30;
  font-size: 13px;
  background: rgba(255, 59, 48, 0.1);
  border-radius: 8px;
  padding: 10px;
}
</style>
