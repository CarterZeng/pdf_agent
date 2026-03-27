function getDefaultApiBaseUrl() {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  if (typeof window !== 'undefined' && window.location?.hostname) {
    return `http://${window.location.hostname}:8000`
  }

  return 'http://127.0.0.1:8000'
}

// API 基础 URL 配置
let API_BASE_URL = getDefaultApiBaseUrl()

/**
 * API 客户端 - 处理所有后端通信
 */
export const api = {
  /**
   * 发送聊天请求
   * @param {string} prompt - 用户问题
   * @returns {Promise<Object>} 返回回答、RAG结果等
   */
  async chat(prompt) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      })

      // ⚠️ 关键错误处理
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `API Error: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Chat API Error:', error)
      throw error
    }
  },

  /**
   * 重新构建 PDF 索引
   * @returns {Promise<Object>} 返回成功消息
   */
  async reindex() {
    try {
      const response = await fetch(`${API_BASE_URL}/reindex`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `API Error: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Reindex API Error:', error)
      throw error
    }
  },

  /**
   * 获取系统健康状态
   * @returns {Promise<Object>} 返回健康检查信息
   */
  async health() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Health Check Error:', error)
      throw error
    }
  },

  /**
   * 清空聊天历史
   * @returns {Promise<Object>} 返回成功消息
   */
  async clearHistory() {
    try {
      const response = await fetch(`${API_BASE_URL}/clear-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `API Error: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Clear History Error:', error)
      throw error
    }
  },

  /**
   * 获取聊天历史
   * @returns {Promise<Object>} 返回历史记录
   */
  async getHistory() {
    try {
      const response = await fetch(`${API_BASE_URL}/history`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `API Error: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Get History Error:', error)
      throw error
    }
  },

  /**
   * 设置 API 基础 URL
   * @param {string} url - 新的 API URL
   */
  setBaseURL(url) {
    API_BASE_URL = url
  },

  /**
   * 获取当前 API 基础 URL
   * @returns {string} API 基础 URL
   */
  getBaseURL() {
    return API_BASE_URL
  },
}
