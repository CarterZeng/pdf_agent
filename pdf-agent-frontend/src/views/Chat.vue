<template>
  <div class="app">
    <!-- 头部 -->
    <header class="header">
      <div class="header-left">
        <div class="logo">📄</div>
        <div class="header-title">
          <h1>PDF Agent</h1>
          <p>学术 RAG 系统</p>
        </div>
      </div>
      <div class="controls">
        <button @click="exportHistory" class="btn btn-export" title="导出聊天记录">
          <span>💾</span>
          <span class="btn-text">导出</span>
        </button>
        <button @click="importHistory" class="btn btn-import" title="导入聊天记录">
          <span>📥</span>
          <span class="btn-text">导入</span>
        </button>
        <input 
          ref="fileInput" 
          type="file" 
          accept=".json" 
          style="display: none"
          @change="handleImport"
        >
        <button @click="reindex" :disabled="isReindexing" class="btn btn-reindex" title="重新构建索引">
          <span>🔄</span>
          <span class="btn-text">重新索引</span>
        </button>
        <button @click="clearHistory" class="btn btn-clear" title="清空对话历史">
          <span>🗑️</span>
          <span class="btn-text">清空</span>
        </button>
        <button @click="logout" class="btn btn-logout" title="退出登录">
          <span>🚪</span>
          <span class="btn-text">退出</span>
        </button>
      </div>
    </header>

    <div class="container">
      <!-- 主聊天区 -->
      <main class="chat-area">
        <div class="messages" ref="messagesContainer">
          <!-- 空状态 -->
          <div v-if="messages.length === 0" class="empty-state">
            <div class="empty-icon">💭</div>
            <h2>开始对话</h2>
            <p>从 PDF 中智能检索答案</p>
            <div class="example-questions">
              <p class="example-title">📝 示例问题：</p>
              <div class="examples">
                <span class="example-item" @click="sendExampleQuery('什么是n-gram模型？')">什么是n-gram模型？</span>
                <span class="example-item" @click="sendExampleQuery('机器学习的核心是什么？')">机器学习的核心</span>
              </div>
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'" class="message-wrapper user-wrapper">
              <div class="message-bubble user-bubble">
                <div class="bubble-text">{{ msg.text }}</div>
              </div>
            </div>

            <!-- AI 回答 -->
            <div v-else class="message-wrapper assistant-wrapper">
              <div class="message-bubble assistant-bubble">
                <!-- 答案内容 -->
                <div class="answer-content" v-html="formatAnswer(msg.text)"></div>

                <!-- 参考文献 -->
                <div v-if="msg.references?.length" class="references-section">
                  <button 
                    class="references-toggle"
                    @click="msg.showReferences = !msg.showReferences"
                  >
                    <span class="toggle-icon">{{ msg.showReferences ? '▼' : '▶' }}</span>
                    {{ msg.showReferences ? '隐藏' : '查看' }}参考文献
                    <span class="ref-count">({{ msg.references.length }})</span>
                  </button>

                  <transition name="slideDown">
                    <div v-if="msg.showReferences" class="references-list">
                      <div v-for="(ref, i) in msg.references" :key="i" class="ref-card">
                        <span class="ref-badge">[{{ ref.ref_id }}]</span>
                        <div class="ref-details">
                          <p class="ref-source">{{ ref.source }}</p>
                          <p class="ref-page">第 {{ ref.page }} 页</p>
                          <p class="ref-excerpt">{{ ref.content.substring(0, 140) }}...</p>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>
              </div>
            </div>
          </div>

          <!-- 加载中 -->
          <div v-if="isLoading" class="message-wrapper assistant-wrapper">
            <div class="message-bubble loading-bubble">
              <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div class="loading-info">
                <span class="loading-text">AI 思考中...</span>
                <span class="timer">⏱️ {{ elapsedTime }}s</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="input-section">
          <textarea
            v-model="inputQuery"
            @keydown.enter.ctrl="sendQuery"
            @keydown.enter.exact.prevent="inputQuery += '\n'"
            placeholder="输入问题 (Ctrl+Enter 发送)..."
            class="input-field"
            :disabled="isLoading"
          ></textarea>
          <button
            @click="sendQuery"
            :disabled="isLoading || !inputQuery.trim()"
            class="btn btn-send"
          >
            {{ isLoading ? '处理中...' : '发送' }}
          </button>
        </div>
      </main>

      <!-- 侧栏 -->
      <aside class="sidebar">
        <!-- 状态卡 -->
        <div class="card">
          <h3>📊 系统状态</h3>
          <div class="status-item">
            <span>API 连接</span>
            <span :class="['status-badge', `status-${apiStatus}`]">
              {{ statusText }}
            </span>
          </div>
          <div class="status-item">
            <span>消息数</span>
            <span class="status-badge">{{ messages.length }}</span>
          </div>
          <div class="status-item">
            <span>存储大小</span>
            <span class="status-badge">{{ storageSize }}</span>
          </div>
          <div class="status-item">
            <span>索引</span>
            <span class="status-badge status-success">✓ 就绪</span>
          </div>
        </div>

        <!-- 使用提示卡 -->
        <div class="card">
          <h3>💡 使用提示</h3>
          <ul class="tips-list">
            <li>输入具体问题答案更精准</li>
            <li>聊天记录可手动清空</li>
            <li>支持JSON格式导出和导入</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, computed, watch } from 'vue'
import { saveChatHistory, loadChatHistory, clearChatHistory as clearStoredHistory, exportChatHistory, importChatHistory } from '../utils/storage'

export default {
  name: 'Chat',
  setup() {
    const inputQuery = ref('')
    const messages = ref([])
    const isLoading = ref(false)
    const isReindexing = ref(false)
    const apiStatus = ref('connecting')
    const apiUrl = 'http://localhost:8000'
    const messagesContainer = ref(null)
    const fileInput = ref(null)
    const elapsedTime = ref(0)
    let timerInterval = null

    const statusText = computed(() => ({
      'connected': '✓ 已连接',
      'connecting': '⏳ 连接中',
      'error': '✗ 已断开'
    }[apiStatus.value]))

    const storageSize = computed(() => {
      const size = JSON.stringify(messages.value).length
      if (size < 1024) return `${size}B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
      return `${(size / (1024 * 1024)).toFixed(1)}MB`
    })

    const formatAnswer = (text) => {
      if (!text) return ''
      
      let html = text
        .replace(/^#{1,6}\s+(.+)$/gm, (match, content) => {
          const level = match.match(/^#+/)[0].length
          return `<span class="answer-heading heading-${level}">${content}</span>`
        })
        .replace(/^\s*[-*•]\s+(.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*?<\/li>)/s, (match) => `<ul class="answer-list">${match}</ul>`)
        .replace(/<\/ul>\s*<ul class="answer-list">/g, '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\[(\d+)\]/g, '<sup class="citation">[引用$1]</sup>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')

      if (!html.startsWith('<p>')) html = '<p>' + html
      if (!html.endsWith('</p>')) html += '</p>'

      return html
    }

    watch(messages, (newMessages) => {
      saveChatHistory(newMessages)
    }, { deep: true })

    const checkHealth = async () => {
      try {
        const res = await fetch(`${apiUrl}/health`)
        apiStatus.value = res.ok ? 'connected' : 'error'
      } catch {
        apiStatus.value = 'error'
      }
    }

    const startTimer = () => {
      elapsedTime.value = 0
      timerInterval = setInterval(() => {
        elapsedTime.value++
      }, 1000)
    }

    const stopTimer = () => {
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
    }

    const scrollToBottom = async () => {
      await nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }

    const sendQuery = async () => {
      if (!inputQuery.value.trim() || isLoading.value) return

      const query = inputQuery.value
      inputQuery.value = ''

      messages.value.push({ role: 'user', text: query })
      isLoading.value = true
      startTimer()
      await scrollToBottom()

      try {
        const response = await fetch(`${apiUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: query, use_history: true })
        })

        if (!response.ok) throw new Error(`HTTP ${response.status}`)

        const data = await response.json()

        messages.value.push({
          role: 'assistant',
          text: data.response,
          references: data.RAG_RESULT || data.rag_results || [],
          showReferences: false
        })
      } catch (error) {
        messages.value.push({
          role: 'assistant',
          text: `❌ 错误: ${error.message}\n\n请检查:\n• 后端是否运行\n• PDF 文件是否存在\n• 是否执行了重新索引`,
          references: []
        })
      } finally {
        isLoading.value = false
        stopTimer()
        await scrollToBottom()
      }
    }

    const sendExampleQuery = (query) => {
      inputQuery.value = query
      sendQuery()
    }

    const reindex = async () => {
      if (!confirm('重新构建索引会重新解析所有PDF，是否继续？')) return

      isReindexing.value = true
      try {
        const res = await fetch(`${apiUrl}/reindex`, { method: 'POST' })
        alert(res.ok ? '✅ 索引构建完成！' : '❌ 索引构建失败')
      } catch (e) {
        alert(`❌ 错误: ${e.message}`)
      } finally {
        isReindexing.value = false
      }
    }

    const clearHistory = async () => {
      if (!confirm('确定清空所有对话？')) return
      try {
        await fetch(`${apiUrl}/clear-history`, { method: 'POST' })
        messages.value = []
        clearStoredHistory()
      } catch (e) {
        alert(`❌ 错误: ${e.message}`)
      }
    }

    const exportHistory = () => {
      exportChatHistory(messages.value)
    }

    const importHistory = () => {
      fileInput.value?.click()
    }

    const handleImport = async (e) => {
      const file = e.target.files?.[0]
      if (!file) return

      try {
        const importedMessages = await importChatHistory(file)
        messages.value = importedMessages
        alert('✅ 导入成功！')
      } catch (error) {
        alert(`❌ 导入失败: ${error.message}`)
      }

      e.target.value = ''
    }

    const logout = () => {
      if (confirm('确定要退出登录吗？')) {
        localStorage.removeItem('user_token')
        localStorage.removeItem('user_info')
        window.location.href = '/login'
      }
    }

    const loadStoredHistory = () => {
      const stored = loadChatHistory()
      if (stored.length > 0) {
        messages.value = stored
      }
    }

    checkHealth()
    loadStoredHistory()

    return {
      inputQuery,
      messages,
      isLoading,
      isReindexing,
      apiStatus,
      statusText,
      storageSize,
      elapsedTime,
      messagesContainer,
      fileInput,
      sendQuery,
      sendExampleQuery,
      reindex,
      clearHistory,
      exportHistory,
      importHistory,
      handleImport,
      logout,
      formatAnswer
    }
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  color: #000 !important;
}

:root {
  --primary: #5b4b8a;
  --primary-light: #7b68b6;
  --primary-dark: #3d2d6b;
  --bg-main: #f8f9fc;
  --bg-card: #ffffff;
  --bg-hover: #f0f2f8;
  --text-primary: #000;
  --text-secondary: #000;
  --border: #e0e5f0;
  --shadow: 0 2px 8px rgba(91, 75, 138, 0.08);
}

.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-main);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
  color: #000 !important;
}

/* ===== 头部 ===== */
.header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #000 !important;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: var(--shadow);
  overflow-x: auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.logo {
  font-size: 28px;
}

.header-title h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: #000 !important;
}

.header-title p {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 2px;
  color: #000 !important;
}

.controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn {
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 12px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  font-family: inherit;
  color: #000 !important;
  background-color: transparent;
  flex-shrink: 0;
}

.btn * {
  color: #000 !important;
}

.btn-text {
  display: inline-block;
  font-size: 12px;
  color: #000 !important;
}

.btn-export,
.btn-import,
.btn-reindex {
  background: rgba(255, 255, 255, 0.9) !important;
  color: #000 !important;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-export:hover,
.btn-import:hover,
.btn-reindex:hover {
  background: rgba(255, 255, 255, 1) !important;
  transform: translateY(-2px);
}

.btn-clear {
  background: rgba(255, 200, 200, 0.9) !important;
  color: #000 !important;
  border: 1px solid rgba(255, 107, 107, 0.4);
}

.btn-clear:hover {
  background: rgba(255, 150, 150, 0.9) !important;
}

.btn-logout {
  background: rgba(255, 107, 107, 0.9) !important;
  color: #000 !important;
  border: 1px solid rgba(255, 107, 107, 0.5);
}

.btn-logout:hover {
  background: rgba(255, 150, 150, 0.9) !important;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ===== 容器 ===== */
.container {
  display: flex;
  flex: 1;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.empty-state h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #000 !important;
}

.empty-state p {
  font-size: 14px;
  color: #000 !important;
  margin-bottom: 24px;
}

.example-questions {
  background: var(--bg-hover);
  padding: 16px;
  border-radius: 10px;
  max-width: 400px;
}

.example-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #000 !important;
}

.examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.example-item {
  padding: 10px 12px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #000 !important;
}

.example-item:hover {
  background: var(--primary);
  color: #000 !important;
  border-color: var(--primary);
}

.message-wrapper {
  display: flex;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-wrapper {
  justify-content: flex-end;
}

.assistant-wrapper {
  justify-content: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  max-width: 70%;
  word-wrap: break-word;
}

.user-bubble {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #000 !important;
  box-shadow: var(--shadow);
}

.user-bubble * {
  color: #000 !important;
}

.bubble-text {
  color: #000 !important;
  font-size: 13.5px;
  line-height: 1.5;
}

.assistant-bubble {
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: #000 !important;
}

.assistant-bubble * {
  color: #000 !important;
}

.loading-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
}

.loading-bubble * {
  color: #000 !important;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: var(--primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

.loading-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: #000 !important;
  font-style: italic;
}

.loading-info * {
  color: #000 !important;
}

.loading-text {
  color: #000 !important;
}

.timer {
  background: var(--primary);
  color: #000 !important;
  padding: 3px 8px;
  border-radius: 5px;
  font-style: normal;
  font-weight: 600;
  min-width: 40px;
  text-align: center;
  font-size: 11px;
}

.answer-content {
  font-size: 13.5px;
  line-height: 1.65;
  word-break: break-word;
  overflow-x: auto;
  color: #000 !important;
}

.answer-content p {
  margin: 0;
  color: #000 !important;
}

.answer-content p + p {
  margin-top: 8px;
}

.answer-heading {
  font-weight: 600;
  color: var(--primary) !important;
}

.answer-heading.heading-1,
.answer-heading.heading-2 {
  font-size: 1.1em;
}

.answer-list {
  margin: 4px 0;
  padding-left: 20px;
  color: #000 !important;
  list-style-type: disc;
}

.answer-list li {
  margin: 3px 0;
  color: #000 !important;
  font-size: 13.5px;
  line-height: 1.6;
}

.answer-content pre {
  background: rgba(91, 75, 138, 0.08);
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 6px 0;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  border-left: 3px solid var(--primary);
  color: #000 !important;
}

.answer-content code {
  color: #000 !important;
}

.inline-code {
  background: rgba(91, 75, 138, 0.1);
  padding: 2px 5px;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  color: var(--primary-dark) !important;
  font-size: 12.5px;
}

.answer-content strong {
  color: var(--primary) !important;
  font-weight: 600;
}

.answer-content em {
  font-style: italic;
  color: #5a6c7d !important;
}

.citation {
  font-size: 11px;
  background: rgba(91, 75, 138, 0.1);
  color: var(--primary) !important;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  margin: 0 2px;
  white-space: nowrap;
  vertical-align: super;
}

.references-section {
  border-top: 1px solid var(--border);
  padding-top: 10px;
  margin-top: 10px;
}

.references-toggle {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-main);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #000 !important;
  font-weight: 600;
  transition: all 0.3s ease;
  font-family: inherit;
  display: flex;
  align-items: center;
  gap: 6px;
}

.references-toggle:hover {
  background: var(--primary);
  color: #000 !important;
  border-color: var(--primary);
}

.toggle-icon {
  font-size: 10px;
  display: inline-block;
}

.ref-count {
  margin-left: auto;
  opacity: 0.8;
  font-size: 11px;
}

.references-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.slideDown-enter-active,
.slideDown-leave-active {
  transition: all 0.3s ease;
}

.slideDown-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slideDown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.ref-card {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-main);
  border-left: 2px solid var(--primary);
  border-radius: 5px;
  font-size: 11.5px;
}

.ref-card * {
  color: #000 !important;
}

.ref-badge {
  background: var(--primary);
  color: #000 !important;
  padding: 3px 6px;
  border-radius: 3px;
  font-weight: 600;
  min-width: 32px;
  text-align: center;
  flex-shrink: 0;
  font-size: 11px;
}

.ref-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ref-source {
  font-weight: 600;
  color: #000 !important;
  margin: 0;
  font-size: 11.5px;
}

.ref-page {
  color: #000 !important;
  font-size: 10px;
  margin: 0;
}

.ref-excerpt {
  color: #000 !important;
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  font-size: 10.5px;
}

.input-section {
  padding: 16px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.input-field {
  flex: 1;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  resize: none;
  max-height: 120px;
  transition: all 0.3s ease;
  background: white;
  color: #000 !important;
}

.input-field:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(91, 75, 138, 0.1);
}

.input-field::placeholder {
  color: #000 !important;
}

.btn-send {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #000 !important;
  padding: 12px 24px;
  min-width: 100px;
  border-radius: 8px;
  font-size: 13px;
}

.btn-send * {
  color: #000 !important;
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(91, 75, 138, 0.12);
}

.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  background: var(--bg-card);
  padding: 16px;
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  color: #000 !important;
}

.card * {
  color: #000 !important;
}

.card h3 {
  font-size: 14px;
  font-weight: 600;
  color: #000 !important;
  margin: 0 0 12px 0;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
  color: #000 !important;
}

.status-item:last-child {
  border-bottom: none;
}

.status-item * {
  color: #000 !important;
}

.status-badge {
  padding: 4px 10px;
  background: var(--bg-hover);
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  color: #000 !important;
}

.status-success {
  color: #000 !important;
}

.tips-list {
  list-style: none;
  font-size: 12px;
  color: #000 !important;
}

.tips-list * {
  color: #000 !important;
}

.tips-list li {
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #000 !important;
}

.tips-list li:before {
  content: '✓';
  color: #000 !important;
  font-weight: 700;
}

.messages::-webkit-scrollbar,
.references-list::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-thumb,
.references-list::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover,
.references-list::-webkit-scrollbar-thumb:hover {
  background: #999;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 240px;
  }
}

@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    flex-direction: row;
  }

  .card {
    flex: 1;
  }

  .message-bubble {
    max-width: 85%;
  }

  .controls {
    flex-wrap: wrap;
  }

  .btn-text {
    display: none;
  }
}
</style>