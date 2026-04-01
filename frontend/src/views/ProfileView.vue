<template>
  <div class="profile">
    <AppHeader
      :balance="userStore.user?.balance ?? 0"
      :photo-url="userStore.user?.photo_url"
      :initials="userStore.getInitials()"
    />

    <!-- ── Персонаж ─────────────────────────────────────────────────── -->
    <section class="profile__section">
      <div class="section-header">
        <span class="section-header__title">Персонаж</span>
      </div>

      <!-- Horizontal snap scroll -->
      <div class="chars-scroll" ref="scrollRef">
        <div
          v-for="char in characters"
          :key="char.id"
          class="char-card"
          :class="{
            'char-card--selected': userStore.user?.character_id === char.id,
            'char-card--preview': previewChar?.id === char.id,
          }"
          @click="onCardTap(char)"
        >
          <!-- Image -->
          <div class="char-card__image">
            <img :src="char.image" :alt="char.name" />
            <!-- Selected badge -->
            <div v-if="userStore.user?.character_id === char.id" class="char-card__badge">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="7" fill="#8127E0"/>
                <path d="M3.5 7L5.8 9.5L10.5 4.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Выбран
            </div>
          </div>

          <!-- Content -->
          <div class="char-card__body">
            <h3 class="char-card__name">{{ char.name }}</h3>
            <p class="char-card__desc">{{ char.shortDesc }}</p>
          </div>

          <!-- Select button overlay (tap-to-select) -->
          <Transition name="fade">
            <div v-if="previewChar?.id === char.id" class="char-card__select-overlay">
              <button
                class="char-card__select-btn"
                :disabled="saving"
                @click.stop="confirmCharacter"
              >
                {{ saving ? '…' : 'Выбрать' }}
              </button>
              <button class="char-card__cancel-btn" @click.stop="previewChar = null">
                Отмена
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Pagination dots -->
      <div class="chars-dots">
        <span
          v-for="char in characters"
          :key="char.id"
          class="chars-dots__dot"
          :class="{ 'chars-dots__dot--active': userStore.user?.character_id === char.id }"
        />
      </div>
    </section>

    <!-- ── Достижения ────────────────────────────────────────────────── -->
    <section class="profile__section">
      <div class="section-header">
        <span class="section-header__title">Достижения</span>
      </div>

      <div v-if="achievementsLoading" class="ach-list">
        <div v-for="i in 3" :key="i" class="skeleton ach-skeleton" />
      </div>

      <div v-else-if="myAchievements.length" class="ach-list">
        <div v-for="(ua, idx) in myAchievements" :key="ua.id">
          <div class="ach-row" :class="{ 'ach-row--claimed': ua.is_claimed }">
            <div class="ach-row__icon-wrap">
              <span class="ach-row__icon">{{ ua.achievement.icon || '🏅' }}</span>
            </div>
            <div class="ach-row__info">
              <span class="ach-row__name">{{ ua.achievement.name }}</span>
              <span class="ach-row__desc">{{ ua.achievement.description }}</span>
            </div>
            <div class="ach-row__right">
              <div class="ach-row__reward">
                <span class="ach-row__coins">+{{ ua.achievement.coins_reward }}</span>
                <img src="@/assets/icons/icon-arcoin.svg" class="ach-row__coin" alt="" />
              </div>
              <button v-if="!ua.is_claimed" class="ach-row__claim" @click="claimAchievement(ua)">
                Забрать
              </button>
              <div v-else class="ach-row__check">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="rgba(52,199,89,0.15)"/>
                  <path d="M5.5 10L8.5 13L14.5 7" stroke="#34C759" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
          </div>
          <div v-if="idx < myAchievements.length - 1" class="ach-row__divider" />
        </div>
      </div>

      <div v-else class="profile__empty">
        <span>🏅</span>
        <p>Достижения появятся после мероприятия</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { achievementsApi } from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'

import bardImg from '@/assets/roles/bard.jpeg'
import kingImg from '@/assets/roles/king.jpeg'
import luchnikImg from '@/assets/roles/luchnik.jpeg'
import tankImg from '@/assets/roles/tank.jpeg'

const userStore = useUserStore()
const myAchievements = ref([])
const achievementsLoading = ref(false)
const previewChar = ref(null)
const saving = ref(false)
const scrollRef = ref(null)

const characters = [
  {
    id: 1,
    name: 'Бард Акаврик',
    image: bardImg,
    shortDesc: 'Мастер историй и песен, способный превратить любой вечер в легенду.',
    fullDesc: `Мастер историй и песен, способный превратить любой вечер в легенду. Собирает вокруг себя толпы слушателей и всегда знает, какую ноту взять… ну, почти всегда.\n\nИскренне верит, что однажды его баллады будут петь по всему миру. А пока — репетирует перед зеркалом и иногда перед случайными прохожими.\n\nТайком записывает свои лучшие строчки в маленький блокнот, который почему-то считает древним артефактом.`,
  },
  {
    id: 2,
    name: 'Рыцарь Акаврик',
    image: kingImg,
    shortDesc: 'Храбрый защитник, для которого честь — не просто слово, а образ жизни.',
    fullDesc: `Храбрый защитник, для которого честь — не просто слово, а образ жизни. Готов встать на пути любой опасности, даже если она слегка больше, чем ожидалось.\n\nДержится с достоинством, как и подобает настоящему герою. И даже в самых сложных ситуациях старается выглядеть внушительно.\n\nКоллекционирует блестящие вещи — "для доспехов", конечно. Почему среди них попадаются пуговицы, лучше не спрашивать.`,
  },
  {
    id: 3,
    name: 'Лучник Акаврик',
    image: luchnikImg,
    shortDesc: 'Точный, сосредоточенный и невероятно уверенный в своём выстреле.',
    fullDesc: `Точный, сосредоточенный и невероятно уверенный в своём выстреле. Видит цель там, где другие видят просто даль.\n\nСтреляет быстро, красиво и с полной уверенностью, что всё идёт строго по плану.\n\nОбожает забираться повыше и наблюдать за всем вокруг, иногда забывая, зачем вообще туда залез.`,
  },
  {
    id: 4,
    name: 'Танк Акаврик',
    image: tankImg,
    shortDesc: 'Непробиваемая стена, за которой спокойно даже в самый разгар боя.',
    fullDesc: `Непробиваемая стена, за которой спокойно даже в самый разгар боя. Там, где другие уклоняются — он просто стоит.\n\nСила, надёжность и абсолютная уверенность в том, что выдержит всё. Ну… почти всё.\n\nЦенит простые радости жизни: уют, отдых… и особенно печеньки с молоком — стратегический ресурс.`,
  },
]

function onCardTap(char) {
  if (userStore.user?.character_id === char.id) return
  previewChar.value = previewChar.value?.id === char.id ? null : char
  window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
}

async function confirmCharacter() {
  if (!previewChar.value || saving.value) return
  saving.value = true
  try {
    await userStore.setCharacter(previewChar.value.id)
    previewChar.value = null
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  } finally {
    saving.value = false
  }
}

async function claimAchievement(ua) {
  try {
    await achievementsApi.claim(ua.achievement.id)
    ua.is_claimed = true
    await userStore.fetchMe()
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  achievementsLoading.value = true
  try {
    const res = await achievementsApi.mine()
    myAchievements.value = res.data
  } finally {
    achievementsLoading.value = false
  }
})
</script>

<style scoped>
.profile {
  min-height: 100%;
  background: #fff;
  padding-top: var(--safe-top);
  padding-bottom: var(--nav-height);
}

.profile__section {
  margin-bottom: 4px;
}

/* ── Character scroll ─────────────────────────────── */
.chars-scroll {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding: 4px 16px 8px;
  /* hide scrollbar */
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.chars-scroll::-webkit-scrollbar { display: none; }

/* ── Character card ───────────────────────────────── */
.char-card {
  flex-shrink: 0;
  width: calc(100vw - 48px);
  scroll-snap-align: center;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 46px 92px rgba(0, 0, 0, 0.04), 0 0 2.86px 1.43px rgba(0, 0, 0, 0.02);
  overflow: hidden;
  border: 2.5px solid transparent;
  transition: border-color 0.2s;
  position: relative;
  cursor: pointer;
}

.char-card--selected {
  border-color: #8127E0;
}

.char-card--preview {
  border-color: rgba(129, 39, 224, 0.4);
}

/* Image */
.char-card__image {
  width: 100%;
  aspect-ratio: 361 / 270;
  position: relative;
  overflow: hidden;
  background: #f0e8ff;
}

.char-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top;
  display: block;
}

/* Selected badge (top-right) */
.char-card__badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  padding: 4px 10px 4px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #8127E0;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Body */
.char-card__body {
  padding: 18px 22px 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.char-card__name {
  font-size: 17px;
  font-weight: 600;
  color: #000;
  letter-spacing: -0.2px;
  line-height: 1.25;
}

.char-card__desc {
  font-size: 13px;
  color: #707579;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Select overlay (appears on tap) */
.char-card__select-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.32);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: 22px;
}

.char-card__select-btn {
  background: #8127E0;
  color: #fff;
  border: none;
  border-radius: 14px;
  padding: 13px 40px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  min-width: 160px;
}
.char-card__select-btn:disabled { opacity: 0.6; }
.char-card__select-btn:not(:disabled):active { opacity: 0.8; }

.char-card__cancel-btn {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: none;
  border-radius: 12px;
  padding: 9px 28px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

/* Pagination dots */
.chars-dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 4px 0 8px;
}

.chars-dots__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(84, 84, 88, 0.25);
  transition: all 0.3s ease;
}

.chars-dots__dot--active {
  width: 18px;
  border-radius: 3px;
  background: #8127E0;
}

/* ── Achievements ────────────────────────────────── */
.ach-list {
  padding: 0 16px;
}

.ach-skeleton {
  height: 60px;
  border-radius: 0;
  margin-bottom: 1px;
}

.ach-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}

.ach-row--claimed { opacity: 0.55; }

.ach-row__icon-wrap {
  width: 44px;
  height: 44px;
  background: rgba(129, 39, 224, 0.08);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ach-row__icon { font-size: 24px; }

.ach-row__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.ach-row__name {
  font-size: 15px;
  font-weight: 600;
  color: #000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ach-row__desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ach-row__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.ach-row__reward {
  display: flex;
  align-items: center;
  gap: 3px;
}

.ach-row__coins {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
}

.ach-row__coin { width: 16px; height: 16px; }

.ach-row__claim {
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 10px;
  cursor: pointer;
}
.ach-row__claim:active { opacity: 0.75; }

.ach-row__check { width: 20px; height: 20px; }

.ach-row__divider {
  height: 0.5px;
  background: rgba(84, 84, 88, 0.45);
  margin-left: 56px;
}

.profile__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 30px 16px;
  color: var(--color-text-secondary);
}

.profile__empty span { font-size: 36px; }
.profile__empty p { font-size: 14px; }
</style>
