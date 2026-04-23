<template>
  <div>
    <h1 class="page-title">Покупки</h1>
    <p class="page-hint">Кто и что купил в мини-аппе: списание аркоинов с баланса.</p>

    <div v-if="loading" class="table-wrap">
      <div v-for="i in 6" :key="i" class="skeleton-row" />
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Когда</th>
            <th>Участник</th>
            <th>Товар</th>
            <th class="text-right">Сумма</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td class="td-date">{{ formatDate(row.created_at) }}</td>
            <td>
              <div class="user-name">
                {{ row.full_name || `${row.first_name} ${row.last_name || ''}`.trim() }}
              </div>
              <div class="user-sub">
                {{ row.username ? '@' + row.username : '—' }} · TG {{ row.telegram_id }}
              </div>
            </td>
            <td>
              <div>{{ row.product_name }}</div>
              <div class="user-sub">id товара {{ row.product_id }}</div>
            </td>
            <td class="text-right">
              <span class="balance">−{{ row.price_paid.toLocaleString('ru') }} 🪙</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!items.length" class="empty">Пока нет покупок</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()
const items = ref([])
const loading = ref(true)

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('ru', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  try {
    items.value = await store.getPurchases()
  } catch (_) {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 24px; font-weight: 700; color: #000; margin-bottom: 8px; letter-spacing: -0.4px; }
.page-hint { font-size: 14px; color: #666; margin: 0 0 20px; max-width: 560px; line-height: 1.4; }
.table-wrap { background: #fff; border-radius: 14px; overflow: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.skeleton-row { height: 54px; background: linear-gradient(90deg,#f4f4f4 25%,#eee 50%,#f4f4f4 75%); background-size:400px 100%; animation:shimmer 1.4s infinite; border-bottom: 1px solid #f0f0f0; }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }
.table { width: 100%; min-width: 640px; border-collapse: collapse; font-size: 14px; }
.table thead th { padding: 12px 16px; font-size: 12px; font-weight: 600; color: #888; text-align: left; border-bottom: 1px solid #f0f0f0; background: #fafafa; }
.table tbody tr { border-bottom: 1px solid #f5f5f5; transition: background 0.1s; }
.table tbody tr:hover { background: #fafafa; }
.table td { padding: 12px 16px; vertical-align: top; }
.td-date { white-space: nowrap; color: #555; font-size: 13px; }
.text-right { text-align: right; }
.user-name { font-weight: 600; color: #000; }
.user-sub { font-size: 12px; color: #999; margin-top: 2px; }
.balance { font-weight: 700; color: #8127E0; }
.empty { padding: 32px; text-align: center; color: #999; }
</style>
