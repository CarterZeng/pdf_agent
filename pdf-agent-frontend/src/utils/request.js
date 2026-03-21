import axios from 'axios'

// 创建axios实例
const service = axios.create({
  baseURL: '/api',  // 对应vite的proxy配置
  timeout: 60000,   // PDF处理超时时间设为60秒
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('Response error:', error)
    ElMessage.error(error.response?.data?.detail || '请求失败，请重试')
    return Promise.reject(error)
  }
)

// 封装接口方法
export const api = {
  // 发送聊天请求
  chat(prompt) {
    return service.post('/chat', { prompt })
  },
  // 重新建立PDF索引
  reindex() {
    return service.post('/reindex')
  }
}