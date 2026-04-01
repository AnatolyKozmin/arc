<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Объявления</h1>
      <button class="btn-primary" @click="openCreate">+ Добавить</button>
    </div>

    <div v-if="loading" class="card-list">
      <div v-for="i in 3" :key="i" class="skeleton-card" />
    </div>

    <div v-else class="card-list">
      <div v-for="item in items" :key="item.id" class="ann-card">
        <div class="ann-card__header">
          <div>
            <p class="ann-card__title">{{ item.title }}</p>
            <div class="ann-card__badges">
              <span class="badge" :class="item.is_active ? 'badge--green' : 'badge--gray'">
                {{ item.is_active ? 'Активно' : 'Неактивно' }}
              </span>
              <span v-if="item.is_draft" class="badge badge--orange">Черновик</span>
              <span class="badge badge--blue">порядок: {{ item.sort_order }}</span>
            </div>
          </div>
          <div class="ann-card__actions">
            <button class="btn-sm" @click="openEdit(item)">✏️ Редактировать</button>
            <button class="btn-sm btn-sm--danger" @click="confirmDelete(item)">🗑️</button>
          </div>
        </div>
        <p v-if="item.description" class="ann-card__desc">{{ item.description }}</p>
        <p v-if="item.image_url" class="ann-card__img-url">🖼 {{ item.image_url }}</p>
      </div>
      <p v-if="!items.length" class="empty">Объявлений нет</p>
    </div>

    <!-- Modal -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = null">
      <div class="modal">
        <h2 class="modal__title">{{ editing ? 'Редактировать' : 'Новое объявление' }}</h2>

        <div class="field">
          <label class="field__label">Заголовок *</label>
          <input v-model="form.title" type="text" class="field__input" placeholder="Аркадиум 2026" />
        </div>
        <div class="field">
          <label class="field__label">Описание</label>
          <textarea v-model="form.description" class="field__input field__textarea" placeholder="Текст объявления…" />
        </div>
        <div class="field">
          <label class="field__label">URL картинки</label>
          <input v-model="form.image_url" type="text" class="field__input" placeholder="https://…" />
        </div>
        <div class="field-row">
          <div class="field">
            <label class="field__label">Порядок</label>
            <input v-model.number="form.sort_order" type="number" class="field__input" />
          </div>
          <label class="toggle">
            <input v-model="form.is_draft" type="checkbox" />
            <span>Черновик</span>
          </label>
          <label class="toggle">
            <input v-model="form.is_active" type="checkbox" />
            <span>Активно</span>
          </label>
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

function defaultForm() {
  return { title: '', description: '', image_url: '', sort_order: 0, is_draft: false, is_active: true }
}

async function load() {
  loading.value = true
  try { items.value = await store.getAnnouncements() }
  finally { loading.value = false }
}

function openCreate() {
  editing.value = null
  form.value = defaultForm()
  formError.value = ''
  modal.value = true
}

function openEdit(item) {
  editing.value = item
  form.value = { title: item.title, description: item.description || '', image_url: item.image_url || '', sort_order: item.sort_order, is_draft: item.is_draft, is_active: item.is_active }
  formError.value = ''
  modal.value = true
}

async function submitForm() {
  if (!form.value.title.trim()) { formError.value = 'Заполните заголовок'; return }
  saving.value = true
  formError.value = ''
  try {
    if (editing.value) {
      const updated = await store.updateAnnouncement(editing.value.id, form.value)
      const idx = items.value.findIndex(i => i.id === updated.id)
      if (idx !== -1) items.value[idx] = updated
    } else {
      const created = await store.createAnnouncement(form.value)
      items.value.unshift(created)
    }
    modal.value = null
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Ошибка'
  } finally {
    saving.value = false
  }
}

async function confirmDelete(item) {
  if (!confirm(`Удалить «${item.title}»?`)) return
  await store.deleteAnnouncement(item.id)
  items.value = items.value.filter(i => i.id !== item.id)
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; color: #000; letter-spacing: -0.4px; }
.btn-primary { background: #8127E0; color: #fff; border: none; border-radius: 10px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
.btn-ghost { background: #f0f0f0; color: #444; border: none; border-radius: 10px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; }

.card-list { display: flex; flex-direction: column; gap: 12px; }
.skeleton-card { height: 90px; border-radius: 14px; background: linear-gradient(90deg,#f4f4f4 25%,#eee 50%,#f4f4f4 75%); background-size:400px 100%; animation:shimmer 1.4s infinite; }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }

.ann-card { background: #fff; border-radius: 14px; padding: 16px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.ann-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.ann-card__title { font-size: 16px; font-weight: 600; color: #000; }
.ann-card__badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.ann-card__actions { display: flex; gap: 8px; flex-shrink: 0; }
.ann-card__desc { font-size: 13px; color: #666; margin-top: 10px; line-height: 1.5; }
.ann-card__img-url { font-size: 12px; color: #999; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { text-align: center; padding: 32px; color: #999; }

.badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
.badge--green { background: rgba(52,199,89,0.12); color: #34C759; }
.badge--gray { background: #f0f0f0; color: #888; }
.badge--orange { background: rgba(255,149,0,0.12); color: #FF9500; }
.badge--blue { background: rgba(0,122,255,0.1); color: #007AFF; }

.btn-sm { background: #f0f0f0; color: #444; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-sm:hover { background: rgba(129,39,224,0.1); color: #8127E0; }
.btn-sm--danger:hover { background: rgba(255,59,48,0.1); color: #ff3b30; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: 14px; max-height: 90vh; overflow-y: auto; }
.modal__title { font-size: 18px; font-weight: 700; }
.modal__actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.field__label { font-size: 13px; font-weight: 600; color: #444; }
.field__input { border: 1.5px solid #e0e0e0; border-radius: 10px; padding: 10px 14px; font-size: 14px; outline: none; }
.field__input:focus { border-color: #8127E0; }
.field__textarea { min-height: 80px; resize: vertical; font-family: inherit; }
.toggle { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; cursor: pointer; padding-bottom: 10px; }
.error-msg { font-size: 13px; color: #ff3b30; }
</style>
