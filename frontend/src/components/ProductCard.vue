<template>
  <div class="product-card" @click="$emit('click', product)">
    <div class="product-card__image">
      <img v-if="product.image_url" :src="product.image_url" :alt="product.name" />
      <div v-else class="product-card__placeholder">
        <span>🎁</span>
      </div>
      <span v-if="product.quantity === 0" class="product-card__badge product-card__badge--sold">Нет</span>
      <span v-else-if="product.quantity <= 3" class="product-card__badge product-card__badge--few">Мало</span>
    </div>
    <div class="product-card__info">
      <p class="product-card__name">{{ product.name }}</p>
      <p class="product-card__price">{{ product.price.toLocaleString('ru') }} Аркоинов</p>
    </div>
  </div>
</template>

<script setup>
defineProps({ product: { type: Object, required: true } })
defineEmits(['click'])
</script>

<style scoped>
.product-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 32px 64px rgba(0, 0, 0, 0.04), 0 0 2px 1px rgba(0, 0, 0, 0.02);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease;
  flex-shrink: 0;
  width: 100%;
}

.product-card:active {
  transform: scale(0.97);
}

.product-card__image {
  width: 100%;
  aspect-ratio: 1;
  position: relative;
  overflow: hidden;
  background: #f5f5f7;
}

.product-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-card__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  background: linear-gradient(135deg, rgba(129, 39, 224, 0.08), #f0e8ff);
}

.product-card__badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 8px;
}

.product-card__badge--few {
  background: rgba(255, 149, 0, 0.15);
  color: #FF9500;
}

.product-card__badge--sold {
  background: rgba(255, 59, 48, 0.12);
  color: #FF3B30;
}

.product-card__info {
  padding: 12px 16px 16px;
}

.product-card__name {
  font-size: 14px;
  font-weight: 600;
  color: #000;
  margin-bottom: 5px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-card__price {
  font-size: 13px;
  font-weight: 500;
  color: #707579;
}
</style>
