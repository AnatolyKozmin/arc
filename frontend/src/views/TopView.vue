<template>
  <div class="top">
    <AppHeader
      :balance="userStore.user?.balance ?? 0"
      :photo-url="userStore.user?.photo_url"
      :initials="userStore.getInitials()"
    />

    <!-- Title row -->
    <div class="top__title-row">
      <h1 class="top__title">Таблица лидеров</h1>
    </div>

    <!-- List -->
    <div class="top__list">
      <div v-if="store.loading" class="top__skeletons">
        <div v-for="i in 8" :key="i" class="skeleton top__skeleton-row" />
      </div>

      <template v-else>
        <div
          v-for="(entry, idx) in store.entries"
          :key="entry.user_id"
        >
          <div
            class="top-row"
            :class="{ 'top-row--me': entry.is_current_user }"
          >
            <div class="top-row__rank-wrap">
              <span class="top-row__rank">{{ entry.rank }}</span>
            </div>

            <UserAvatar
              :photo-url="entry.photo_url"
              :initials="getInitials(entry)"
              :size="40"
              :active-outline="entry.is_current_user"
            />

            <div class="top-row__info">
              <span class="top-row__name">
                {{ entry.first_name }}{{ entry.last_name ? ' ' + entry.last_name : '' }}
                <span v-if="entry.rank === 1"> 🥇</span>
                <span v-else-if="entry.rank === 2"> 🥈</span>
                <span v-else-if="entry.rank === 3"> 🥉</span>
              </span>
              <span v-if="entry.username" class="top-row__sub">@{{ entry.username }}</span>
            </div>

            <div class="top-row__score">
              <span class="top-row__coins">{{ formatScore(entry.balance) }}</span>
              <img src="@/assets/icons/icon-arcoin.svg" class="top-row__coin" alt="" />
            </div>
          </div>

          <!-- Divider (except after last) -->
          <div v-if="idx < store.entries.length - 1" class="top-row__divider" />
        </div>
      </template>

      <div v-if="!store.loading && !store.entries.length" class="top__empty">
        Рейтинг пока пуст
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useLeaderboardStore } from '@/stores/leaderboard'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/AppHeader.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const store = useLeaderboardStore()
const userStore = useUserStore()

function getInitials(entry) {
  return ((entry.first_name?.[0] ?? '') + (entry.last_name?.[0] ?? '')).toUpperCase() || 'TG'
}

function formatScore(n) {
  if (!n && n !== 0) return '0'
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1).replace('.', ',') + 'к'
  return n.toLocaleString('ru')
}

onMounted(() => store.fetch())
</script>

<style scoped>
.top {
  min-height: 100%;
  background: #fff;
  padding-top: var(--safe-top);
  padding-bottom: var(--nav-height);
}

/* Title */
.top__title-row {
  padding: 14px 16px 10px;
}

.top__title {
  font-size: 22px;
  font-weight: 590;
  color: #000;
  letter-spacing: -0.24px;
}

/* List */
.top__list {
  padding: 0 16px;
}

.top__skeletons {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.top__skeleton-row {
  height: 58px;
  border-radius: 0;
  margin-bottom: 1px;
}

.top-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  background: transparent;
}

.top-row--me {
  background: rgba(129, 39, 224, 0.04);
  border-radius: 12px;
  padding: 10px 8px;
  margin: 0 -8px;
}

.top-row__rank-wrap {
  width: 24px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.top-row__rank {
  font-size: 15.5px;
  font-weight: 400;
  color: #000;
  text-align: center;
  line-height: 1.33;
  letter-spacing: -0.24px;
}

.top-row__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
  margin-left: 4px;
}

.top-row__name {
  font-size: 15px;
  font-weight: 600;
  color: #000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.33;
}

.top-row__sub {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.3;
}

.top-row__score {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.top-row__coins {
  font-size: 15.5px;
  font-weight: 400;
  color: #000;
  line-height: 1.33;
  letter-spacing: -0.24px;
}

.top-row__coin {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.top-row__divider {
  height: 0.5px;
  background: rgba(84, 84, 88, 0.45);
  margin-left: 76px;
}

.top__empty {
  padding: 40px 0;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 15px;
}
</style>
