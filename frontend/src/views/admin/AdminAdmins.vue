<template>
  <div class="admin-admins">
    <div class="page-header">
      <h1>Администраторы</h1>
      <button class="btn btn-primary" @click="showAdd = true">+ Добавить</button>
    </div>

    <div class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Telegram ID</th>
            <th>Заметка</th>
            <th>Добавлен</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="admin in admins" :key="admin.id">
            <td><code>{{ admin.telegram_id }}</code></td>
            <td>{{ admin.note || '—' }}</td>
            <td>{{ new Date(admin.created_at).toLocaleDateString('ru') }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="removeAdmin(admin.telegram_id)">
                Удалить
              </button>
            </td>
          </tr>
          <tr v-if="!admins.length">
            <td colspan="4" class="empty-row">Нет дополнительных администраторов</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="hint">
      Администраторы из .env (ADMIN_TELEGRAM_IDS) работают всегда и здесь не отображаются.
    </p>

    <!-- Модал добавления -->
    <div v-if="showAdd" class="modal-overlay" @click.self="showAdd = false">
      <div class="modal">
        <h2>Добавить администратора</h2>
        <div class="form-group">
          <label>Telegram ID</label>
          <input v-model.number="newId" type="number" placeholder="123456789" />
        </div>
        <div class="form-group">
          <label>Заметка (необязательно)</label>
          <input v-model="newNote" type="text" placeholder="Имя или роль" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showAdd = false">Отмена</button>
          <button class="btn btn-primary" @click="addAdmin" :disabled="!newId || saving">
            {{ saving ? 'Сохранение…' : 'Добавить' }}
          </button>
        </div>
        <p v-if="addError" class="form-error">{{ addError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const admins = ref([])
const showAdd = ref(false)
const saving = ref(false)
const addError = ref(null)
const newId = ref(null)
const newNote = ref('')

async function load() {
  try {
    const res = await adminStore.http.get('/panel/admins')
    admins.value = res.data
  } catch (e) {
    console.error(e)
  }
}

async function addAdmin() {
  if (!newId.value) return
  saving.value = true
  addError.value = null
  try {
    await adminStore.http.post('/panel/admins', {
      telegram_id: newId.value,
      note: newNote.value || null,
    })
    newId.value = null
    newNote.value = ''
    showAdd.value = false
    await load()
  } catch (e) {
    addError.value = e.response?.data?.detail || 'Ошибка'
  } finally {
    saving.value = false
  }
}

async function removeAdmin(telegramId) {
  if (!confirm(`Удалить администратора ${telegramId}?`)) return
  try {
    await adminStore.http.delete(`/panel/admins/${telegramId}`)
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Ошибка')
  }
}

onMounted(load)
</script>

<style scoped>
.admin-admins { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h1 { font-size: 24px; font-weight: 700; }
.hint { margin-top: 12px; font-size: 13px; color: #6c757d; }
.form-error { color: #dc3545; font-size: 13px; margin-top: 8px; }
</style>
