<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Товары</h1>
      <button class="btn-primary" @click="openCreate">+ Добавить товар</button>
    </div>

    <div v-if="loading" class="grid">
      <div v-for="i in 4" :key="i" class="skeleton-card" />
    </div>

    <div v-else class="grid">
      <div v-for="item in items" :key="item.id" class="product-card">
        <div class="product-card__img">
          <img v-if="item.image_url" :src="item.image_url" :alt="item.name" />
          <span v-else>🎁</span>
        </div>
        <div class="product-card__body">
          <div class="product-card__top">
            <p class="product-card__name">{{ item.name }}</p>
            <div class="product-card__badges">
              <span class="badge badge--purple">{{ item.price }} 🪙</span>
              <span class="badge" :class="item.quantity > 0 ? 'badge--green' : 'badge--red'">{{ item.quantity }} шт.</span>
              <span v-if="item.is_featured" class="badge badge--orange">⭐ Featured</span>
              <span v-if="!item.is_active" class="badge badge--gray">Скрыт</span>
            </div>
          </div>
          <p v-if="item.description" class="product-card__desc">{{ item.description }}</p>
          <div class="product-card__actions">
            <button class="btn-sm" @click="openEdit(item)">✏️ Редактировать</button>
            <button class="btn-sm btn-sm--danger" @click="confirmDelete(item)">🗑️ Удалить</button>
          </div>
        </div>
      </div>
      <p v-if="!items.length" class="empty">Товаров нет</p>
    </div>

    <!-- Modal -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = null">
      <div class="modal">
        <h2 class="modal__title">{{ editing ? 'Редактировать товар' : 'Новый товар' }}</h2>

        <div class="field">
          <label class="field__label">Название *</label>
          <input v-model="form.name" type="text" class="field__input" placeholder="Футболка с Аркавриком" />
        </div>
        <div class="field">
          <label class="field__label">Описание</label>
          <textarea v-model="form.description" class="field__input field__textarea" placeholder="Описание товара…" />
        </div>
        <div class="field">
          <label class="field__label">Изображение</label>
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            class="field__input field__file"
            :disabled="uploading"
            @change="onImageFile"
          />
          <p class="field__hint">Загрузка файла или укажите ссылку ниже</p>
          <input v-model="form.image_url" type="text" class="field__input" placeholder="https://… или /api/uploads/…" />
          <div v-if="form.image_url" class="img-preview-wrap">
            <img :src="form.image_url" alt="" class="img-preview" />
          </div>
        </div>
        <div class="field-row">
          <div class="field field--sm">
            <label class="field__label">Цена (аркоины) *</label>
            <input v-model.number="form.price" type="number" min="0" class="field__input" />
          </div>
          <div class="field field--sm">
            <label class="field__label">Количество *</label>
            <input v-model.number="form.quantity" type="number" min="0" class="field__input" />
          </div>
        </div>
        <div class="field-row">
          <label class="toggle">
            <input v-model="form.is_featured" type="checkbox" />
            <span>⭐ Показать на главной</span>
          </label>
          <label v-if="editing" class="toggle">
            <input v-model="form.is_active" type="checkbox" />
            <span>Активен</span>
          </label>
        </div>

        <p v-if="formError" class="error-msg">{{ formError }}</p>

        <div class="modal__actions">
          <button class="btn-ghost" @click="modal = null">Отмена</button>
          <button class="btn-primary" :disabled="saving || uploading" @click="submitForm">
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
const uploading = ref(false)
const formError = ref('')
const form = ref(defaultForm())

function defaultForm() {
  return { name: '', description: '', image_url: '', price: 0, quantity: 10, is_featured: false, is_active: true }
}

async function load() {
  loading.value = true
  try { items.value = await store.getProducts() }
  finally { loading.value = false }
}

function openCreate() {
  editing.value = null; form.value = defaultForm(); formError.value = ''; modal.value = true
}

function openEdit(item) {
  editing.value = item
  form.value = { name: item.name, description: item.description || '', image_url: item.image_url || '', price: item.price, quantity: item.quantity, is_featured: item.is_featured, is_active: item.is_active }
  formError.value = ''; modal.value = true
}

async function submitForm() {
  if (!form.value.name.trim()) { formError.value = 'Заполните название'; return }
  if (form.value.price < 0) { formError.value = 'Цена не может быть отрицательной'; return }
  saving.value = true; formError.value = ''
  try {
    if (editing.value) {
      const updated = await store.updateProduct(editing.value.id, form.value)
      const idx = items.value.findIndex(i => i.id === updated.id)
      if (idx !== -1) items.value[idx] = updated
    } else {
      const created = await store.createProduct(form.value)
      items.value.push(created)
    }
    modal.value = null
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Ошибка'
  } finally {
    saving.value = false
  }
}

async function onImageFile(e) {
  const f = e.target?.files?.[0]
  if (!f) return
  uploading.value = true
  formError.value = ''
  try {
    form.value.image_url = await store.uploadImage(f)
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Ошибка загрузки файла'
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function confirmDelete(item) {
  if (!confirm(`Удалить «${item.name}»?`)) return
  await store.deleteProduct(item.id)
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

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.skeleton-card { height: 200px; border-radius: 14px; background: linear-gradient(90deg,#f4f4f4 25%,#eee 50%,#f4f4f4 75%); background-size:400px 100%; animation:shimmer 1.4s infinite; }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }

.product-card { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: flex; flex-direction: column; }
.product-card__img { width: 100%; aspect-ratio: 3/2; background: #f5f5f7; display: flex; align-items: center; justify-content: center; font-size: 40px; overflow: hidden; }
.product-card__img img { width:100%; height:100%; object-fit: cover; }
.product-card__body { padding: 14px 16px 16px; flex: 1; display: flex; flex-direction: column; gap: 8px; }
.product-card__top { display: flex; flex-direction: column; gap: 6px; }
.product-card__name { font-size: 15px; font-weight: 600; color: #000; }
.product-card__badges { display: flex; flex-wrap: wrap; gap: 5px; }
.product-card__desc { font-size: 12px; color: #888; line-height: 1.4; flex: 1; }
.product-card__actions { display: flex; gap: 8px; margin-top: 4px; }
.empty { text-align: center; padding: 32px; color: #999; grid-column: 1/-1; }

.badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
.badge--purple { background: rgba(129,39,224,0.1); color: #8127E0; }
.badge--green { background: rgba(52,199,89,0.12); color: #34C759; }
.badge--red { background: rgba(255,59,48,0.1); color: #ff3b30; }
.badge--orange { background: rgba(255,149,0,0.12); color: #FF9500; }
.badge--gray { background: #f0f0f0; color: #888; }

.btn-sm { background: #f0f0f0; color: #444; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-sm:hover { background: rgba(129,39,224,0.1); color: #8127E0; }
.btn-sm--danger:hover { background: rgba(255,59,48,0.1); color: #ff3b30; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: 14px; max-height: 90vh; overflow-y: auto; }
.modal__title { font-size: 18px; font-weight: 700; }
.modal__actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field--sm { flex: 1; }
.field-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.field__label { font-size: 13px; font-weight: 600; color: #444; }
.field__input { border: 1.5px solid #e0e0e0; border-radius: 10px; padding: 10px 14px; font-size: 14px; outline: none; width: 100%; box-sizing: border-box; }
.field__input:focus { border-color: #8127E0; }
.field__textarea { min-height: 80px; resize: vertical; font-family: inherit; }
.field__hint { font-size: 12px; color: #888; margin: -4px 0 4px; }
.field__file { padding: 8px 0; font-size: 13px; }
.img-preview-wrap { margin-top: 8px; }
.img-preview { max-height: 120px; max-width: 100%; border-radius: 10px; object-fit: contain; background: #f5f5f7; }
.toggle { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; cursor: pointer; padding-bottom: 10px; }
.error-msg { font-size: 13px; color: #ff3b30; }
</style>
