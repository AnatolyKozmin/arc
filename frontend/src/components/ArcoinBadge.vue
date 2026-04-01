<template>
  <div class="arcoin-badge">
    <span class="arcoin-badge__amount">{{ amount.toLocaleString('ru') }}</span>
    <span class="arcoin-badge__icon">🪙</span>
  </div>
</template>

<script setup>
defineProps({
  amount: { type: Number, required: true },
})
</script>

<style scoped>
.arcoin-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--color-accent-light);
  border-radius: 20px;
  padding: 4px 10px 4px 8px;
}

.arcoin-badge__amount {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-accent);
  letter-spacing: -0.3px;
}

.arcoin-badge__icon {
  font-size: 16px;
  line-height: 1;
}
</style>
