import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)

// 使用 Element Plus 组件库
app.use(ElementPlus)

app.mount('#app')