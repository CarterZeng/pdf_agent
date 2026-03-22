import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Chat from './views/Chat.vue'
import './style.css'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Chat',
    component: Chat
  }
]

// 创建路由器
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 检查登录状态
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('user_token')
  
  if (to.path === '/login') {
    next()
  } else if (token) {
    next()
  } else {
    next('/login')
  }
})

// 创建应用
const app = createApp(App)

app.use(router)
app.mount('#app')