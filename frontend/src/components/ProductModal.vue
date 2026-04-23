<template>
  <Teleport to="body">
    <Transition name="slide-up">
      <div v-if="product" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal">
          <div class="modal__handle" />

          <div class="modal__image">
            <img v-if="product.image_url" :src="product.image_url" :alt="product.name" />
            <div v-else class="modal__image-placeholder">
              <span>🎁</span>
            </div>
          </div>

          <div class="modal__body">
            <div class="modal__header">
              <h2 class="modal__title">{{ product.name }}</h2>
              <div class="modal__price">{{ product.price.toLocaleString('ru') }} 🪙</div>
            </div>

            <div class="modal__stock" :class="stockClass">
              <span>{{ stockText }}</span>
            </div>

            <p v-if="product.description" class="modal__desc">{{ product.description }}</p>

            <div class="modal__notice">
              <span class="modal__notice-icon">ℹ️</span>
              <p>
                С баланса спишутся аркоины. Выдача приза — на <strong>ярмарке</strong> во время мероприятия.
              </p>
            </div>

            <p v-if="buyError" class="modal__error">{{ buyError }}</p>

            <button
              v-if="canBuy"
              class="modal__buy-btn"
              :disabled="buying"
              @click="buy"
            >
              {{ buying ? '…' : `Купить за ${product.price.toLocaleString('ru')} 🪙` }}
            </button>
            <button
              v-else-if="product.quantity > 0 && !canAfford"
              class="modal__buy-btn modal__buy-btn--muted"
              disabled
            >
              Недостаточно аркоинов
            </button>

            <button class="modal__close-btn" @click="$emit('close')">Закрыть</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { productsApi, apiErrorMessage } from '@/api/client'
import { useUserStore } from '@/stores/user'

const props = defineProps({ product: { type: Object, default: null } })
const emit = defineEmits(['close', 'purchased'])

const userStore = useUserStore()
const buying = ref(false)
const buyError = ref('')

watch(
  () => props.product?.id,
  () => {
    buyError.value = ''
  }
)

const canAfford = computed(() => {
  const b = userStore.user?.balance ?? 0
  const p = props.product?.price ?? 0
  return b >= p
})

const canBuy = computed(() => {
  if (!props.product) return false
  return props.product.quantity > 0 && canAfford.value
})

async function buy() {
  if (!props.product || buying.value || !canBuy.value) return
  buying.value = true
  buyError.value = ''
  try {
    const { data } = await productsApi.purchase(props.product.id)
    if (userStore.user) userStore.user.balance = data.balance
    emit('purchased', data)
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  } catch (e) {
    const d = e.response?.data?.detail
    buyError.value = apiErrorMessage(e, 'Не удалось оформить покупку')
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
  } finally {
    buying.value = false
  }
}

const stockClass = computed(() => {
  if (!props.product) return ''
  if (props.product.quantity === 0) return 'modal__stock--sold'
  if (props.product.quantity <= 3) return 'modal__stock--few'
  return 'modal__stock--ok'
})

const stockText = computed(() => {
  if (!props.product) return ''
  if (props.product.quantity === 0) return 'Нет в наличии'
  if (props.product.quantity <= 3) return `Осталось ${props.product.quantity} шт`
  return `В наличии ${props.product.quantity} шт`
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 200;
  display: flex;
  align-items: flex-end;
}

.modal {
  width: 100%;
  background: var(--color-surface);
  border-radius: 24px 24px 0 0;
  max-height: 90dvh;
  overflow-y: auto;
  padding-bottom: calc(24px + var(--safe-bottom));
}

.modal__handle {
  width: 36px;
  height: 4px;
  background: var(--color-separator);
  border-radius: 2px;
  margin: 12px auto 0;
}

.modal__image {
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
}

.modal__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal__image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64px;
  background: linear-gradient(135deg, var(--color-accent-light), #f0e8ff);
}

.modal__body {
  padding: 20px 20px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.modal__title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.3px;
  flex: 1;
}

.modal__price {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
}

.modal__stock {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 10px;
  width: fit-content;
}

.modal__stock--ok { background: rgba(52, 199, 89, 0.12); color: var(--color-green); }
.modal__stock--few { background: rgba(255, 149, 0, 0.12); color: var(--color-orange); }
.modal__stock--sold { background: rgba(255, 59, 48, 0.1); color: var(--color-red); }

.modal__desc {
  font-size: 15px;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.modal__notice {
  display: flex;
  gap: 10px;
  background: var(--color-bg);
  border-radius: 12px;
  padding: 14px;
}

.modal__notice-icon { font-size: 18px; flex-shrink: 0; }

.modal__notice p {
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.modal__error {
  font-size: 14px;
  color: var(--color-red);
  margin: 0;
  text-align: center;
}

.modal__buy-btn {
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 14px;
  background: var(--color-accent);
  font-size: 17px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
}

.modal__buy-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.modal__buy-btn--muted {
  background: var(--color-bg);
  color: var(--color-text-secondary);
}

.modal__close-btn {
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 14px;
  background: var(--color-bg);
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  cursor: pointer;
}
</style>
