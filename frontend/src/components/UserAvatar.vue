<template>
  <div
    class="avatar"
    :class="{ 'avatar--active': activeOutline }"
    :style="{ width: size + 'px', height: size + 'px' }"
  >
    <img v-if="photoUrl" :src="photoUrl" alt="avatar" class="avatar__img" />
    <span v-else class="avatar__initials" :style="{ fontSize: size * 0.33 + 'px' }">
      {{ initials }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  photoUrl: { type: String, default: null },
  initials: { type: String, default: 'TG' },
  size: { type: Number, default: 40 },
  activeOutline: { type: Boolean, default: false },
})
</script>

<style scoped>
.avatar {
  border-radius: 50%;
  background: rgba(67, 120, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar--active {
  outline: 2.5px solid #8127E0;
  outline-offset: 1.5px;
}

.avatar__initials {
  font-weight: 590;
  color: #007AFF;
  letter-spacing: -0.3px;
}
</style>
