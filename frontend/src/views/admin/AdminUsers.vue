<template>
  <div>
    <h1 class="page-title">Участники</h1>

    <div class="toolbar">
      <input
        v-model="search"
        class="search"
        type="text"
        placeholder="Поиск по имени или @username…"
        @input="loadUsers"
      />
      <button type="button" class="btn-add" @click="openAddUser">
        + Добавить по @username
      </button>
      <button
        type="button"
        class="btn-export"
        :disabled="exportLoading"
        @click="downloadExport"
      >
        {{ exportLoading ? 'Готовим файл…' : '⬇ Excel: регистрация на мероприятие' }}
      </button>
    </div>
    <p v-if="exportError" class="export-error">{{ exportError }}</p>
    <p class="toolbar-hint">
      Выгрузка Excel — только участники с заполненной <b>регистрацией на мероприятие</b> (как в боте / мини-аппе).
    </p>

    <div v-if="loading" class="table-wrap">
      <div v-for="i in 6" :key="i" class="skeleton-row" />
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Имя</th>
            <th>Telegram</th>
            <th>Вуз / Курс</th>
            <th class="text-right">Аркоины</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <div class="user-name">{{ user.full_name || `${user.first_name} ${user.last_name || ''}`.trim() }}</div>
              <div class="user-sub">{{ user.is_registered ? '✅ зарегистрирован' : '⏳ не зарегистрирован' }}</div>
            </td>
            <td>
              <div>{{ user.username ? '@' + user.username : '—' }}</div>
              <div class="user-sub">ID {{ user.telegram_id }}</div>
            </td>
            <td>
              <div>{{ user.university || '—' }}</div>
              <div v-if="user.course" class="user-sub">{{ user.course }} курс, {{ user.group || '' }}</div>
            </td>
            <td class="text-right">
              <span class="balance">{{ user.balance.toLocaleString('ru') }} 🪙</span>
            </td>
            <td class="text-right">
              <button class="btn-sm" @click="openBalance(user)">± Аркоины</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!users.length" class="empty">Участники не найдены</p>
    </div>

    <!-- Balance modal -->
    <div v-if="balanceModal" class="modal-overlay" @click.self="balanceModal = null">
      <div class="modal">
        <h2 class="modal__title">Начислить / списать аркоины</h2>
        <p class="modal__user">{{ balanceModal.full_name || balanceModal.first_name }} — {{ balanceModal.balance }} 🪙</p>

        <div class="field">
          <label class="field__label">Сумма (отрицательная = списание)</label>
          <input v-model.number="balanceAmount" type="number" class="field__input" placeholder="100" />
        </div>
        <div class="field">
          <label class="field__label">Причина</label>
          <input v-model="balanceReason" type="text" class="field__input" placeholder="Победа в турнире" />
        </div>

        <p v-if="balanceError" class="error-msg">{{ balanceError }}</p>

        <div class="modal__actions">
          <button class="btn-ghost" @click="balanceModal = null">Отмена</button>
          <button class="btn-primary" :disabled="saving" @click="submitBalance">
            {{ saving ? '…' : 'Применить' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Добавить участника по @username (getChat) -->
    <div v-if="addModal" class="modal-overlay" @click.self="addModal = false">
      <div class="modal">
        <h2 class="modal__title">Добавить по @username</h2>
        <p class="modal__hint">
          Публичный username в Telegram (латиница, без @). Человек должен хотя бы раз нажать
          <strong>Start</strong> у вашего бота или написать ему — иначе Telegram не отдаёт профиль по имени.
          Если уже в базе — обновим имя и @username из Telegram.
        </p>

        <div class="field">
          <label class="field__label">Username *</label>
          <input
            v-model="addPublicUsername"
            type="text"
            class="field__input"
            placeholder="username или @username"
            autocomplete="off"
          />
        </div>

        <p v-if="addError" class="error-msg">{{ addError }}</p>

        <div class="modal__actions">
          <button class="btn-ghost" @click="addModal = false">Отмена</button>
          <button
            class="btn-primary"
            :disabled="addSaving || !addPublicUsername.trim()"
            @click="submitAddUser"
          >
            {{ addSaving ? '…' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()
const users = ref([])
const loading = ref(true)
const search = ref('')
const balanceModal = ref(null)
const balanceAmount = ref(0)
const balanceReason = ref('')
const balanceError = ref('')
const saving = ref(false)

const addModal = ref(false)
const addPublicUsername = ref('')
const addError = ref('')
const addSaving = ref(false)
const exportLoading = ref(false)
const exportError = ref('')

function openAddUser() {
  addModal.value = true
  addPublicUsername.value = ''
  addError.value = ''
}

function normalizeUsername(raw) {
  const s = (raw || '').trim().replace(/^@/, '').trim()
  return s || null
}

async function submitAddUser() {
  const u = normalizeUsername(addPublicUsername.value)
  if (!u) {
    addError.value = 'Укажите username'
    return
  }
  addSaving.value = true
  addError.value = ''
  try {
    await store.ensureUserByUsername({ username: u })
    addModal.value = false
    search.value = ''
    await loadUsers()
  } catch (e) {
    const d = e.response?.data?.detail
    addError.value = Array.isArray(d)
      ? d.map((x) => x.msg || x).join('; ')
      : (typeof d === 'string' ? d : 'Ошибка сохранения')
  } finally {
    addSaving.value = false
  }
}

async function loadUsers() {
  loading.value = true
  try { users.value = await store.getUsers(search.value) }
  finally { loading.value = false }
}

async function downloadExport() {
  exportError.value = ''
  exportLoading.value = true
  try {
    await store.exportUsersXlsx()
  } catch (e) {
    let msg = 'Не удалось скачать файл'
    if (e.response?.data instanceof Blob) {
      try {
        const t = await e.response.data.text()
        const j = JSON.parse(t)
        if (j.detail) msg = typeof j.detail === 'string' ? j.detail : msg
      } catch (_) {
        msg = e.message || msg
      }
    } else {
      msg = e.response?.data?.detail || e.message || msg
    }
    exportError.value = msg
  } finally {
    exportLoading.value = false
  }
}

function openBalance(user) {
  balanceModal.value = user
  balanceAmount.value = 0
  balanceReason.value = ''
  balanceError.value = ''
}

async function submitBalance() {
  if (!balanceAmount.value) { balanceError.value = 'Введите сумму'; return }
  if (!balanceReason.value.trim()) { balanceError.value = 'Укажите причину'; return }
  saving.value = true
  balanceError.value = ''
  try {
    const updated = await store.updateBalance(balanceModal.value.id, balanceAmount.value, balanceReason.value)
    const idx = users.value.findIndex(u => u.id === updated.id)
    if (idx !== -1) users.value[idx] = updated
    balanceModal.value = null
  } catch (e) {
    balanceError.value = e.response?.data?.detail || 'Ошибка'
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.page-title { font-size: 24px; font-weight: 700; color: #000; margin-bottom: 20px; letter-spacing: -0.4px; }
.toolbar {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.search {
  flex: 1;
  min-width: 200px;
  max-width: 360px;
  border: 1.5px solid #e0e0e0; border-radius: 10px;
  padding: 10px 14px; font-size: 14px; outline: none;
  transition: border-color 0.15s;
}
.search:focus { border-color: #8127E0; }

.table-wrap { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.skeleton-row { height: 54px; background: linear-gradient(90deg,#f4f4f4 25%,#eee 50%,#f4f4f4 75%); background-size:400px 100%; animation:shimmer 1.4s infinite; border-bottom: 1px solid #f0f0f0; }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }

.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table thead th { padding: 12px 16px; font-size: 12px; font-weight: 600; color: #888; text-align: left; border-bottom: 1px solid #f0f0f0; background: #fafafa; }
.table tbody tr { border-bottom: 1px solid #f5f5f5; transition: background 0.1s; }
.table tbody tr:hover { background: #fafafa; }
.table td { padding: 12px 16px; vertical-align: middle; }
.text-right { text-align: right; }
.user-name { font-weight: 600; color: #000; }
.user-sub { font-size: 12px; color: #999; margin-top: 2px; }
.balance { font-weight: 700; color: #8127E0; }
.empty { padding: 32px; text-align: center; color: #999; }

.btn-sm { background: #f0f0f0; color: #333; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.btn-sm:hover { background: rgba(129,39,224,0.1); color: #8127E0; }

.btn-add {
  background: #8127E0;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-add:hover { filter: brightness(1.05); }
.btn-add:active { transform: scale(0.98); }

.btn-export {
  background: #fff;
  color: #333;
  border: 1.5px solid #8127E0;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-export:hover:not(:disabled) { background: rgba(129, 39, 224, 0.06); }
.btn-export:disabled { opacity: 0.65; cursor: default; }

.export-error { font-size: 13px; color: #dc3545; margin: -8px 0 12px; }
.toolbar-hint { font-size: 13px; color: #666; margin: -4px 0 14px; max-width: 640px; line-height: 1.4; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 100%; max-width: 420px; display: flex; flex-direction: column; gap: 16px; }
.modal__title { font-size: 18px; font-weight: 700; }
.modal__user { font-size: 14px; color: #666; margin-top: -8px; }
.modal__hint { font-size: 13px; color: #666; line-height: 1.45; margin: -8px 0 4px; }
.modal__actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field__label { font-size: 13px; font-weight: 600; color: #444; }
.field__input { border: 1.5px solid #e0e0e0; border-radius: 10px; padding: 10px 14px; font-size: 14px; outline: none; }
.field__input:focus { border-color: #8127E0; }
.error-msg { font-size: 13px; color: #ff3b30; }
.btn-primary { background: #8127E0; color: #fff; border: none; border-radius: 10px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
.btn-ghost { background: #f0f0f0; color: #444; border: none; border-radius: 10px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; }
</style>
