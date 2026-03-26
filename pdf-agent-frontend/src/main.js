import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Chat from './views/Chat.vue'
import './style.css'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Chat',
    component: Chat,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ✅ 使用 async/await 替代弃用的 next() 回调
router.beforeEach(async (to) => {
  const token = localStorage.getItem('user_token')
  
  // 未登录用户只能访问登录页
  if (!token && to.path !== '/login') {
    return '/login'
  }
  
  // 已登录用户自动跳转出登录页
  if (token && to.path === '/login') {
    return '/'
  }
  
  // 允许访问
  return true
})

const app = createApp(App)
app.use(router)
app.mount('#app')