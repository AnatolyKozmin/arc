<template>
  <div class="register">
    <div class="register__header">
      <div class="register__logo">
        <ArcadiumIcon />
      </div>
      <h1 class="register__title">Добро пожаловать!</h1>
      <p class="register__subtitle">Зарегистрируйтесь для участия в Аркадиуме</p>
    </div>

    <form class="register__form" @submit.prevent="submit">
      <div class="register__field">
        <label class="register__label">ФИО</label>
        <input
          v-model="form.full_name"
          class="register__input"
          type="text"
          placeholder="Иванов Иван Иванович"
          required
          autocomplete="name"
        />
      </div>

      <div class="register__field">
        <label class="register__label">ВУЗ</label>
        <input
          v-model="form.university"
          class="register__input"
          type="text"
          placeholder="Финансовый университет"
          required
        />
      </div>

      <div class="register__row">
        <div class="register__field" style="flex:1">
          <label class="register__label">Курс</label>
          <select v-model="form.course" class="register__input" required>
            <option value="" disabled>Выберите</option>
            <option v-for="n in 6" :key="n" :value="n">{{ n }} курс</option>
          </select>
        </div>

        <div class="register__field" style="flex:1">
          <label class="register__label">Группа</label>
          <input
            v-model="form.group"
            class="register__input"
            type="text"
            placeholder="ПИ21-1"
            required
          />
        </div>
      </div>

      <button class="register__btn" type="submit" :disabled="loading">
        <span v-if="loading">Регистрируемся...</span>
        <span v-else>Зарегистрироваться 🎮</span>
      </button>

      <p v-if="error" class="register__error">{{ error }}</p>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useUserStore } from '@/stores/user'
import ArcadiumIcon from '@/components/ArcadiumIcon.vue'

const userStore = useUserStore()
const loading = ref(false)
const error = ref('')

const form = reactive({
  full_name: '',
  university: 'Финансовый университет при Правительстве РФ',
  course: '',
  group: '',
})

async function submit() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  try {
    await userStore.register({
      full_name: form.full_name,
      university: form.university,
      course: Number(form.course),
      group: form.group,
    })
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Ошибка регистрации'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding: calc(var(--safe-top) + 20px) 20px calc(var(--safe-bottom) + 24px);
  background: var(--color-bg);
}

.register__header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.register__logo {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  overflow: hidden;
}

.register__title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
  text-align: center;
}

.register__subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  text-align: center;
  line-height: 1.4;
}

.register__form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.register__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.register__row {
  display: flex;
  gap: 12px;
}

.register__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  padding-left: 4px;
}

.register__input {
  width: 100%;
  padding: 14px 16px;
  border: 1.5px solid var(--color-separator);
  border-radius: 12px;
  background: var(--color-surface);
  font-size: 16px;
  color: var(--color-text-primary);
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
  appearance: none;
}

.register__input:focus {
  border-color: var(--color-accent);
}

.register__btn {
  width: 100%;
  padding: 16px;
  background: var(--color-accent);
  color: white;
  font-size: 17px;
  font-weight: 700;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  margin-top: 8px;
  transition: opacity 0.15s, transform 0.1s;
}

.register__btn:active { transform: scale(0.98); }
.register__btn:disabled { opacity: 0.6; cursor: default; }

.register__error {
  font-size: 13px;
  color: var(--color-red);
  text-align: center;
  padding: 4px;
}
</style>
