import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import TopView from '@/views/TopView.vue'
import ShopView from '@/views/ShopView.vue'
import ProfileView from '@/views/ProfileView.vue'

// Lazy-load admin views
const AdminLogin = () => import('@/views/admin/AdminLogin.vue')
const AdminLayout = () => import('@/views/admin/AdminLayout.vue')
const AdminDashboard = () => import('@/views/admin/AdminDashboard.vue')
const AdminUsers = () => import('@/views/admin/AdminUsers.vue')
const AdminAnnouncements = () => import('@/views/admin/AdminAnnouncements.vue')
const AdminProducts = () => import('@/views/admin/AdminProducts.vue')
const AdminAchievements = () => import('@/views/admin/AdminAchievements.vue')

const routes = [
  // Mobile app routes
  { path: '/', name: 'home', component: HomeView },
  { path: '/top', name: 'top', component: TopView },
  { path: '/shop', name: 'shop', component: ShopView },
  { path: '/profile', name: 'profile', component: ProfileView },

  // Admin panel
  { path: '/admin/login', name: 'admin-login', component: AdminLogin },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: AdminDashboard },
      { path: 'users', name: 'admin-users', component: AdminUsers },
      { path: 'announcements', name: 'admin-announcements', component: AdminAnnouncements },
      { path: 'products', name: 'admin-products', component: AdminProducts },
      { path: 'achievements', name: 'admin-achievements', component: AdminAchievements },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// Guard for admin routes
router.beforeEach((to) => {
  if (to.meta.requiresAdmin) {
    const token = localStorage.getItem('panel_token')
    if (!token) return { path: '/admin/login' }
  }
})

export default router
