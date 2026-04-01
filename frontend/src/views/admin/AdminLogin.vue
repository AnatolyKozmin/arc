<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-card__logo">
        <span class="login-card__emoji">🎮</span>
        <h1 class="login-card__title">Аркадиум</h1>
        <p class="login-card__sub">Панель администратора</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field">
          <label class="field__label">Логин</label>
          <input
            v-model="username"
            type="text"
            class="field__input"
            placeholder="admin"
            autocomplete="username"
            required
          />
        </div>

        <div class="field">
          <label class="field__label">Пароль</label>
          <input
            v-model="password"
            type="password"
            class="field__input"
            placeholder="••••••••"
            autocomplete="current-password"
            required
          />
        </div>

        <p v-if="store.error" class="login-form__error">{{ store.error }}</p>

        <button type="submit" class="login-btn" :disabled="store.loading">
          <span v-if="store.loading">Вхожу…</span>
          <span v-else>Войти</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()
const router = useRouter()
const username = ref('')
const password = ref('')

async function handleLogin() {
  const ok = await store.login(username.value, password.value)
  if (ok) router.push('/admin')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
}

.login-card {
  background: #fff;
  border-radius: 20px;
  padding: 40px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 4px 32px rgba(0,0,0,0.10);
}

.login-card__logo {
  text-align: center;
  margin-bottom: 32px;
}

.login-card__emoji { font-size: 48px; }

.login-card__title {
  font-size: 26px;
  font-weight: 700;
  color: #000;
  margin: 8px 0 4px;
  letter-spacing: -0.5px;
}

.login-card__sub {
  font-size: 14px;
  color: #6e6e71;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field__label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.field__input {
  border: 1.5px solid #e0e0e0;
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.15s;
  background: #fafafa;
}

.field__input:focus {
  border-color: #8127E0;
  background: #fff;
}

.login-form__error {
  font-size: 13px;
  color: #ff3b30;
  text-align: center;
}

.login-btn {
  background: #8127E0;
  color: #fff;
  border: none;
  border-radius: 12px;
  padding: 13px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 4px;
  transition: opacity 0.15s;
}

.login-btn:disabled { opacity: 0.6; cursor: default; }
.login-btn:not(:disabled):hover { opacity: 0.9; }
</style>
