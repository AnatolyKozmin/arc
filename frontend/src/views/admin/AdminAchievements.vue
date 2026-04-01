<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Достижения</h1>
      <button class="btn-primary" @click="openCreate">+ Добавить</button>
    </div>

    <div v-if="loading" class="ach-list">
      <div v-for="i in 4" :key="i" class="skeleton-row" />
    </div>

    <div v-else class="ach-list">
      <div v-for="item in items" :key="item.id" class="ach-row">
        <div class="ach-row__icon">{{ item.icon || '🏅' }}</div>
        <div class="ach-row__info">
          <p class="ach-row__name">{{ item.name }}</p>
          <p class="ach-row__desc">{{ item.description }}</p>
          <div class="ach-row__badges">
            <span class="badge badge--purple">+{{ item.coins_reward }} 🪙</span>
            <span class="badge badge--blue">{{ item.achievement_type }}</span>
            <span v-if="!item.is_active" class="badge badge--gray">Неактивно</span>
          </div>
        </div>
        <div class="ach-row__actions">
          <button class="btn-sm" @click="openAssign(item)">👤 Выдать</button>
          <button class="btn-sm" @click="openEdit(item)">✏️</button>
          <button class="btn-sm btn-sm--danger" @click="confirmDelete(item)">🗑️</button>
        </div>
      </div>
      <p v-if="!items.length" class="empty">Достижений нет</p>
    </div>

    <!-- Achievement form modal -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = null">
      <div class="modal">
        <h2 class="modal__title">{{ editing ? 'Редактировать достижение' : 'Новое достижение' }}</h2>

        <div class="field-row">
          <div class="field field--sm">
            <label class="field__label">Иконка (эмодзи)</label>
            <input v-model="form.icon" type="text" class="field__input" placeholder="🏆" maxlength="4" />
          </div>
          <div class="field" style="flex:3">
            <label class="field__label">Название *</label>
            <input v-model="form.name" type="text" class="field__input" placeholder="Чемпион турнира" />
          </div>
        </div>
        <div class="field">
          <label class="field__label">Описание</label>
          <textarea v-model="form.description" class="field__input field__textarea" placeholder="Что нужно сделать…" />
        </div>
        <div class="field-row">
          <div class="field field--sm">
            <label class="field__label">Награда (аркоины)</label>
            <input v-model.number="form.coins_reward" type="number" min="0" class="field__input" />
          </div>
          <div class="field field--sm">
            <label class="field__label">Тип</label>
            <select v-model="form.achievement_type" class="field__input">
              <option value="manual">manual (вручную)</option>
              <option value="auto">auto (автоматически)</option>
            </select>
          </div>
        </div>

        <p v-if="formError" class="error-msg">{{ formError }}</p>

        <div class="modal__actions">
          <button class="btn-ghost" @click="modal = null">Отмена</button>
          <button class="btn-primary" :disabled="saving" @click="submitForm">
            {{ saving ? '…' : (editing ? 'Сохранить' : 'Создать') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Assign modal -->
    <div v-if="assignModal" class="modal-overlay" @click.self="assignModal = null">
      <div class="modal">
        <h2 class="modal__title">Выдать: {{ assignModal.name }}</h2>

        <div class="field">
          <label class="field__label">Поиск участника</label>
          <input v-model="assignSearch" type="text" class="field__input" placeholder="Имя или @username" @input="searchUsers" />
        </div>

        <div class="user-list">
          <div
            v-for="u in assignUsers"
            :key="u.id"
            class="user-item"
            :class="{ 'user-item--selected': assignUserId === u.id }"
            @click="assignUserId = u.id"
          >
            <div class="user-item__name">{{ u.full_name || u.first_name }}</div>
            <div class="user-item__sub">{{ u.username ? '@' + u.username : 'ID ' + u.telegram_id }}</div>
          </div>
          <p v-if="!assignUsers.length && assignSearch" class="empty-sm">Не найдено</p>
        </div>

        <p v-if="assignError" class="error-msg">{{ assignError }}</p>

        <div class="modal__actions">
          <button class="btn-ghost" @click="assignModal = null">Отмена</button>
          <button class="btn-primary" :disabled="!assignUserId || assignSaving" @click="submitAssign">
            {{ assignSaving ? '…' : 'Выдать' }}
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
const items = ref([])
const loading = ref(true)
const modal = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const form = ref(defaultForm())

const assignModal = ref(null)
const assignSearch = ref('')
const assignUsers = ref([])
const assignUserId = ref(null)
const assignError = ref('')
const assignSaving = ref(false)

function defaultForm() {
  return { name: '', description: '', icon: '🏅', coins_reward: 100, achievement_type: 'manual' }
}

async function load() {
  loading.value = true
  try { items.value = await store.getAchievements() }
  finally { loading.value = false }
}

function openCreate() { editing.value = null; form.value = defaultForm(); formError.value = ''; modal.value = true }

function openEdit(item) {
  editing.value = item
  form.value = { name: item.name, description: item.description || '', icon: item.icon || '🏅', coins_reward: item.coins_reward, achievement_type: item.achievement_type }
  formError.value = ''; modal.value = true
}

async function submitForm() {
  if (!form.value.name.trim()) { formError.value = 'Заполните название'; return }
  saving.value = true; formError.value = ''
  try {
    if (editing.value) {
      const updated = await store.updateAchievement(editing.value.id, form.value)
      const idx = items.value.findIndex(i => i.id === updated.id)
      if (idx !== -1) items.value[idx] = updated
    } else {
      items.value.push(await store.createAchievement(form.value))
    }
    modal.value = null
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Ошибка'
  } finally { saving.value = false }
}

async function confirmDelete(item) {
  if (!confirm(`Удалить «${item.name}»?`)) return
  await store.deleteAchievement(item.id)
  items.value = items.value.filter(i => i.id !== item.id)
}

function openAssign(item) {
  assignModal.value = item; assignSearch.value = ''; assignUsers.value = []; assignUserId.value = null; assignError.value = ''
}

async function searchUsers() {
  if (!assignSearch.value.trim()) { assignUsers.value = []; return }
  assignUsers.value = await store.getUsers(assignSearch.value, 0, 10)
}

async function submitAssign() {
  if (!assignUserId.value) return
  assignSaving.value = true; assignError.value = ''
  try {
    await store.assignAchievement(assignUserId.value, assignModal.value.id)
    assignModal.value = null
  } catch (e) {
    assignError.value = e.response?.data?.detail || 'Ошибка'
  } finally { assignSaving.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; color: #000; letter-spacing: -0.4px; }
.btn-primary { background: #8127E0; color: #fff; border: none; border-radius: 10px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-ghost { background: #f0f0f0; color: #444; border: none; border-radius: 10px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; }

.ach-list { display: flex; flex-direction: column; gap: 8px; }
.skeleton-row { height: 70px; border-radius: 12px; background: linear-gradient(90deg,#f4f4f4 25%,#eee 50%,#f4f4f4 75%); background-size:400px 100%; animation:shimmer 1.4s infinite; }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }

.ach-row { background: #fff; border-radius: 12px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: flex; align-items: center; gap: 14px; }
.ach-row__icon { font-size: 30px; flex-shrink: 0; }
.ach-row__info { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ach-row__name { font-size: 15px; font-weight: 600; color: #000; }
.ach-row__desc { font-size: 12px; color: #888; }
.ach-row__badges { display: flex; gap: 5px; flex-wrap: wrap; }
.ach-row__actions { display: flex; gap: 6px; flex-shrink: 0; }
.empty { text-align: center; padding: 32px; color: #999; }

.badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
.badge--purple { background: rgba(129,39,224,0.1); color: #8127E0; }
.badge--blue { background: rgba(0,122,255,0.1); color: #007AFF; }
.badge--gray { background: #f0f0f0; color: #888; }

.btn-sm { background: #f0f0f0; color: #444; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.btn-sm:hover { background: rgba(129,39,224,0.1); color: #8127E0; }
.btn-sm--danger:hover { background: rgba(255,59,48,0.1); color: #ff3b30; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 100%; max-width: 460px; display: flex; flex-direction: column; gap: 14px; max-height: 90vh; overflow-y: auto; }
.modal__title { font-size: 18px; font-weight: 700; }
.modal__actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field--sm { flex: 1; }
.field-row { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
.field__label { font-size: 13px; font-weight: 600; color: #444; }
.field__input { border: 1.5px solid #e0e0e0; border-radius: 10px; padding: 10px 14px; font-size: 14px; outline: none; width: 100%; box-sizing: border-box; }
.field__input:focus { border-color: #8127E0; }
.field__textarea { min-height: 70px; resize: vertical; font-family: inherit; }
.error-msg { font-size: 13px; color: #ff3b30; }

.user-list { max-height: 200px; overflow-y: auto; border: 1.5px solid #f0f0f0; border-radius: 10px; }
.user-item { padding: 10px 14px; cursor: pointer; border-bottom: 1px solid #f5f5f5; transition: background 0.1s; }
.user-item:hover { background: #fafafa; }
.user-item--selected { background: rgba(129,39,224,0.08); }
.user-item__name { font-size: 14px; font-weight: 600; color: #000; }
.user-item__sub { font-size: 12px; color: #999; }
.empty-sm { padding: 14px; text-align: center; color: #999; font-size: 13px; }
</style>
