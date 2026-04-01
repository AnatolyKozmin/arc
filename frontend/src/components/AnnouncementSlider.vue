<template>
  <div class="slider" @touchstart="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd">
    <div class="slider__track" :style="trackStyle">
      <div
        v-for="item in items"
        :key="item.id"
        class="slider__slide"
      >
        <div
          class="slide__bg"
          :style="item.image_url ? { backgroundImage: `url(${item.image_url})` } : {}"
        >
          <div class="slide__gradient" />
          <div class="slide__content">
            <h3 class="slide__title">{{ item.title }}</h3>
            <p v-if="item.description" class="slide__desc">{{ item.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination capsule -->
    <div v-if="items.length > 1" class="slider__pagination">
      <span
        v-for="(_, idx) in items"
        :key="idx"
        class="slider__dot"
        :class="{ 'slider__dot--active': idx === current }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  items: { type: Array, required: true },
  intervalMs: { type: Number, default: 6500 },
})

const current = ref(0)
let autoTimer = null

const trackStyle = computed(() => ({
  transform: `translateX(-${current.value * 100}%)`,
  transition: 'transform 0.4s cubic-bezier(0.32, 0.72, 0, 1)',
}))

function next() {
  current.value = (current.value + 1) % props.items.length
}

function startAuto() {
  if (props.items.length <= 1) return
  autoTimer = setInterval(next, props.intervalMs)
}

function stopAuto() {
  clearInterval(autoTimer)
}

onMounted(startAuto)
onBeforeUnmount(stopAuto)

watch(() => props.items.length, () => {
  current.value = 0
  stopAuto()
  startAuto()
})

let touchStartX = 0
let touchDeltaX = 0

function onTouchStart(e) {
  touchStartX = e.touches[0].clientX
  stopAuto()
}

function onTouchMove(e) {
  touchDeltaX = e.touches[0].clientX - touchStartX
}

function onTouchEnd() {
  if (Math.abs(touchDeltaX) > 40) {
    if (touchDeltaX < 0) {
      current.value = Math.min(current.value + 1, props.items.length - 1)
    } else {
      current.value = Math.max(current.value - 1, 0)
    }
  }
  touchDeltaX = 0
  startAuto()
}
</script>

<style scoped>
.slider {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  margin: 0 16px;
  /* Figma: 360×236 aspect ratio */
  aspect-ratio: 360 / 236;
}

.slider__track {
  display: flex;
  height: 100%;
}

.slider__slide {
  flex: 0 0 100%;
  height: 100%;
}

.slide__bg {
  width: 100%;
  height: 100%;
  background-color: #40087A;
  background-size: cover;
  background-position: center;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

/* Figma gradient: -74deg, purple 50% → transparent 64% */
.slide__gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    -74deg,
    rgba(129, 39, 224, 1) 0%,
    rgba(129, 39, 224, 0.9) 40%,
    rgba(129, 39, 224, 0) 64%
  );
}

.slide__content {
  position: relative;
  z-index: 1;
  padding: 16px 20px 20px;
}

.slide__title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 4px;
  letter-spacing: -0.3px;
  line-height: 1.25;
}

.slide__desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Figma: backdrop-blur capsule in bottom-right */
.slider__pagination {
  position: absolute;
  bottom: 10px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(44px);
  -webkit-backdrop-filter: blur(44px);
  border-radius: 28px;
  padding: 5px 8px;
  z-index: 2;
}

.slider__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.slider__dot--active {
  width: 18px;
  height: 6px;
  border-radius: 3px;
  background: #fff;
}
</style>
