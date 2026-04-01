<template>
  <div class="app-header">
    <div class="app-header__row">
      <div class="app-header__balance">
        <span class="app-header__amount">{{ balance.toLocaleString('ru') }}</span>
        <img src="@/assets/icons/icon-arcoin.svg" class="app-header__coin" alt="arcoin" />
      </div>
      <UserAvatar
        :photo-url="photoUrl"
        :initials="initials"
        :size="40"
      />
    </div>
    <div class="app-header__divider" />
  </div>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'

defineProps({
  balance: { type: Number, default: 0 },
  photoUrl: { type: String, default: null },
  initials: { type: String, default: 'TG' },
})
</script>

<style scoped>
.app-header {
  background: #fff;
}

.app-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}

.app-header__balance {
  display: flex;
  align-items: center;
  gap: 6px;
}

.app-header__amount {
  font-size: 18.5px;
  font-weight: 590;
  color: #000;
  letter-spacing: -0.28px;
  line-height: 1.33;
}

.app-header__coin {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.app-header__divider {
  height: 0.5px;
  background: rgba(84, 84, 88, 0.45);
  margin: 0 16px;
}
</style>
