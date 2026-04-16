<template>
  <div class="scan">
    <AppHeader
      :balance="userStore.user?.balance ?? 0"
      :photo-url="userStore.user?.photo_url"
      :initials="userStore.getInitials()"
    />

    <div class="scan__body">
      <h2 class="scan__title">Сканер QR</h2>
      <p class="scan__sub">Наведи камеру на QR-код участника</p>

      <button class="scan__btn" @click="openScanner" :disabled="scanning">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <path d="M14 14h2v2h-2zM18 14h3M14 18h2M18 18h3v3M21 14v2"/>
        </svg>
        {{ scanning ? 'Сканирую…' : 'Открыть сканер' }}
      </button>

      <!-- Результат сканирования -->
      <Transition name="slide-up">
        <div v-if="scannedUser" class="scan__result">
          <div class="scan__user">
            <UserAvatar
              :photo-url="scannedUser.photo_url"
              :initials="getInitials(scannedUser)"
              :size="56"
            />
            <div class="scan__user-info">
              <span class="scan__user-name">{{ scannedUser.full_name || scannedUser.first_name }}</span>
              <span class="scan__user-meta">
                {{ scannedUser.university || '—' }}
                <span v-if="scannedUser.course"> · {{ scannedUser.course }} курс</span>
              </span>
              <div class="scan__user-balance">
                <span>{{ scannedUser.balance.toLocaleString('ru') }}</span>
                <img src="@/assets/icons/icon-arcoin.svg" width="16" height="16" alt="" />
              </div>
            </div>
          </div>

          <!-- Быстрое начисление -->
          <div class="scan__actions">
            <p class="scan__actions-label">Начислить аркоины:</p>
            <div class="scan__presets">
              <button
                v-for="amount in presets"
                :key="amount"
                class="scan__preset"
                @click="quickAdd(amount)"
                :disabled="adding"
              >+{{ amount }}</button>
            </div>
            <div class="scan__custom">
              <input
                v-model.number="customAmount"
                type="number"
                placeholder="Своя сумма"
                class="scan__input"
                min="1"
              />
              <button class="scan__add-btn" @click="quickAdd(customAmount)" :disabled="adding || !customAmount">
                {{ adding ? '…' : 'Начислить' }}
              </button>
            </div>
          </div>

          <button class="scan__close" @click="scannedUser = null">Закрыть</button>
        </div>
      </Transition>

      <!-- Ошибка -->
      <div v-if="error" class="scan__error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { useLeaderboardStore } from '@/stores/leaderboard'
import client from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const userStore = useUserStore()
const leaderboardStore = useLeaderboardStore()
const scanning = ref(false)
const adding = ref(false)
const scannedUser = ref(null)
const error = ref(null)
const customAmount = ref(null)
const presets = [10, 25, 50, 100]

function getInitials(user) {
  if (!user) return 'TG'
  const parts = [user.first_name, user.last_name].filter(Boolean)
  return parts.map(p => p[0]).join('').toUpperCase() || 'TG'
}

async function openScanner() {
  error.value = null
  const tg = window.Telegram?.WebApp

  if (!tg?.showScanQrPopup) {
    // Fallback: manual input for dev mode
    const token = prompt('Введи QR токен (dev mode):')
    if (token) await lookupToken(token.trim())
    return
  }

  scanning.value = true
  tg.showScanQrPopup({ text: 'Наведи на QR-код участника' }, async (data) => {
    scanning.value = false
    await lookupToken(data)
    return true
  })
}

/** Убираем пробелы/переносы из QR; tg id — только цифры (иначе бэкенд искал бы по qr_token → 404). */
function normalizeScanPayload(raw) {
  const s = String(raw ?? '').trim()
  if (!s) return ''
  const compact = s.replace(/\s+/g, '')
  if (/^\d{4,20}$/.test(compact)) return compact
  return s
}

async function lookupToken(token) {
  const normalized = normalizeScanPayload(token)
  if (!normalized) return
  scanning.value = true
  error.value = null
  try {
    const enc = encodeURIComponent(normalized)
    const res = await client.get(`/users/scan/${enc}`)
    scannedUser.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'QR-код не найден'
    scannedUser.value = null
  } finally {
    scanning.value = false
  }
}

async function quickAdd(amount) {
  if (!amount || !scannedUser.value || adding.value) return
  adding.value = true
  try {
    const res = await client.post(`/users/${scannedUser.value.id}/balance`, {
      amount,
      reason: 'Начисление организатором (QR)',
    })
    scannedUser.value = res.data
    leaderboardStore.fetch({ force: true })
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    customAmount.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка начисления'
  } finally {
    adding.value = false
  }
}
</script>

<style scoped>
.scan {
  min-height: 100%;
  background: #fff;
  padding-top: var(--safe-top);
  padding-bottom: var(--nav-height);
}

.scan__body {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.scan__title {
  font-size: 22px;
  font-weight: 700;
  color: #000;
}

.scan__sub {
  font-size: 14px;
  color: var(--color-text-secondary);
  text-align: center;
}

.scan__btn {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #8127E0;
  color: #fff;
  border: none;
  border-radius: 16px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.scan__btn:disabled { opacity: 0.6; }
.scan__btn:not(:disabled):active { opacity: 0.8; }

/* Result card */
.scan__result {
  width: 100%;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scan__user {
  display: flex;
  align-items: center;
  gap: 14px;
}

.scan__user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.scan__user-name {
  font-size: 16px;
  font-weight: 600;
  color: #000;
}

.scan__user-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.scan__user-balance {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #8127E0;
  margin-top: 2px;
}

.scan__actions-label {
  font-size: 13px;
  font-weight: 600;
  color: #000;
}

.scan__presets {
  display: flex;
  gap: 8px;
}

.scan__preset {
  flex: 1;
  background: rgba(129, 39, 224, 0.1);
  color: #8127E0;
  border: none;
  border-radius: 10px;
  padding: 10px 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.scan__preset:active { opacity: 0.7; }
.scan__preset:disabled { opacity: 0.4; }

.scan__custom {
  display: flex;
  gap: 8px;
}

.scan__input {
  flex: 1;
  border: 1.5px solid rgba(84,84,88,0.2);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
}
.scan__input:focus { border-color: #8127E0; }

.scan__add-btn {
  background: #8127E0;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.scan__add-btn:disabled { opacity: 0.5; }

.scan__close {
  background: rgba(84,84,88,0.1);
  color: #000;
  border: none;
  border-radius: 12px;
  padding: 10px;
  font-size: 14px;
  cursor: pointer;
  width: 100%;
}

.scan__error {
  color: #ff3b30;
  font-size: 14px;
  text-align: center;
  padding: 8px 16px;
  background: rgba(255,59,48,0.08);
  border-radius: 10px;
  width: 100%;
}

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(20px); }
.slide-up-leave-to { opacity: 0; transform: translateY(20px); }
</style>
