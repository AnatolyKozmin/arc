import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

// Expand immediately so there's no white area before Vue mounts
try {
  window.Telegram?.WebApp?.expand()
  window.Telegram?.WebApp?.ready()
} catch {}

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
