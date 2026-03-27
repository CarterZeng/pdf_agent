<template>
  <div class="chat-page">
    <div v-if="isMobile && isSidebarOpen" class="mobile-mask" @click="closeSidebar"></div>

    <aside :class="['sidebar', { open: isSidebarOpen, mobile: isMobile }]">
      <div class="sidebar-header">
        <button class="sidebar-primary" @click="requestClearHistory">New chat</button>
        <button v-if="isMobile" class="sidebar-close" @click="closeSidebar">Close</button>
      </div>

      <div class="sidebar-brand">
        <div class="brand-badge">PA</div>
        <div>
          <strong>PDF Agent</strong>
          <p>Academic workspace</p>
        </div>
      </div>

      <div class="sidebar-group">
        <div class="sidebar-label-row">
          <span class="sidebar-label">Chats</span>
          <span class="sidebar-count">{{ conversationItems.length }}</span>
        </div>

        <div v-if="conversationItems.length" class="conversation-list">
          <button
            v-for="item in conversationItems"
            :key="item.id"
            class="conversation-item"
            :class="{ active: activeConversationId === item.id }"
            @click="jumpToConversation(item)"
          >
            <strong>{{ item.title }}</strong>
            <p>{{ item.preview }}</p>
          </button>
        </div>
        <div v-else class="conversation-empty">Brief records of each exchange will appear here.</div>
      </div>

      <div class="sidebar-group sidebar-status">
        <div class="sidebar-label-row">
          <span class="sidebar-label">Index</span>
          <span :class="['status-pill', `status-${systemStatusTone}`]">{{ systemStatusLabel }}</span>
        </div>
        <p class="status-copy">{{ systemHeadline }}</p>
        <div class="status-meta">
          <span>{{ healthInfo.indexed_pdf_count || 0 }} PDFs</span>
          <span>{{ formattedIndexTimer }}</span>
        </div>
      </div>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <div class="topbar-left">
          <button class="ghost-icon-btn" @click="toggleSidebar">≡</button>
          <div class="topbar-title">PDF Agent</div>
        </div>

        <div class="topbar-actions">
          <button class="quiet-btn" @click="exportHistory">Export</button>
          <button class="quiet-btn" @click="importHistory">Import</button>
          <button class="quiet-btn" :disabled="isReindexing" @click="requestReindex">
            {{ isReindexing ? 'Rebuilding' : 'Rebuild index' }}
          </button>
          <button class="quiet-btn" @click="requestLogout">Sign out</button>
          <input
            ref="fileInput"
            type="file"
            accept=".json"
            class="hidden-input"
            @change="handleImport"
          >
        </div>
      </header>

      <section class="chat-shell">
        <div ref="messagesContainer" class="messages-panel">
          <div v-if="messages.length === 0" class="empty-chat-state">
            <h2>Which paper would you like to explore first?</h2>
            <p>Ask directly and the system will answer from the current PDF index with cited evidence.</p>

            <div class="starter-list">
              <button class="starter-btn" @click="sendExampleQuery('Summarize the main idea of the paper.')">
                Summarize the paper
              </button>
              <button class="starter-btn" @click="sendExampleQuery('What method does the paper propose?')">
                Extract the method
              </button>
              <button class="starter-btn" @click="sendExampleQuery('Compare the papers in the PDF library.')">
                Compare papers
              </button>
            </div>
          </div>

          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            :ref="(el) => registerMessageRef(el, idx)"
            :class="['message-row', msg.role]"
          >
            <div :class="['avatar', msg.role === 'user' ? 'avatar-user' : 'avatar-agent']">
              {{ msg.role === 'user' ? 'U' : 'PA' }}
            </div>

            <div class="message-block">
              <div class="message-meta">
                <strong>{{ msg.role === 'user' ? 'You' : 'PDF Agent' }}</strong>
              </div>

              <div v-if="msg.role === 'user'" class="user-bubble">
                {{ msg.text }}
              </div>

              <div v-else class="assistant-bubble">
                <div class="answer-content" v-html="formatAnswer(msg.text)"></div>

                <div v-if="msg.references?.length" class="reference-panel">
                  <button class="reference-toggle" @click="msg.showReferences = !msg.showReferences">
                    <span>{{ msg.showReferences ? 'Hide references' : 'Show references' }}</span>
                    <span class="reference-count">{{ msg.references.length }}</span>
                  </button>

                  <div v-if="!msg.showReferences" class="reference-preview-list">
                    <div v-for="(ref, i) in msg.references.slice(0, 2)" :key="`preview-${i}`" class="reference-preview-item">
                      <strong>Ref {{ ref.ref_id }}</strong>
                      <span>{{ ref.source }}</span>
                      <p>{{ truncate(ref.content, 88) }}</p>
                    </div>
                  </div>

                  <div v-if="msg.showReferences" class="reference-list">
                    <div v-for="(ref, i) in msg.references" :key="i" class="reference-item">
                      <div class="reference-meta">
                        <strong>Ref {{ ref.ref_id }}</strong>
                        <span>{{ ref.source }}</span>
                        <span>Page {{ ref.page }}</span>
                      </div>
                      <div class="reference-content" v-html="formatAnswer(ref.content)"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isLoading" class="message-row assistant">
            <div class="avatar avatar-agent">PA</div>
            <div class="message-block">
              <div class="message-meta">
                <strong>PDF Agent</strong>
              </div>
              <div class="assistant-bubble loading-bubble">
                <div class="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <p>Retrieving evidence and drafting the answer. Elapsed: {{ elapsedTime }}s</p>
              </div>
            </div>
          </div>
        </div>

        <footer class="composer-shell">
          <div class="composer-box">
            <textarea
              v-model="inputQuery"
              class="composer-input"
              :disabled="isLoading || !canSend"
              placeholder="Send a message to PDF Agent. Press Ctrl + Enter to submit."
              @keydown.enter.ctrl.prevent="sendQuery"
              @keydown.enter.exact.prevent="inputQuery += '\n'"
            ></textarea>
            <button
              class="send-btn"
              :disabled="isLoading || !inputQuery.trim() || !canSend"
              @click="sendQuery"
            >
              {{ isLoading ? 'Sending' : 'Send' }}
            </button>
          </div>
        </footer>
      </section>
    </main>

    <transition name="toast">
      <div v-if="toast.visible" :class="['toast', `toast-${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <transition name="modal">
      <div v-if="dialog.visible" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog-card">
          <h3>{{ dialog.title }}</h3>
          <p>{{ dialog.message }}</p>
          <div class="dialog-actions">
            <button class="dialog-btn ghost" @click="closeDialog">Cancel</button>
            <button class="dialog-btn solid" @click="confirmDialog">Continue</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  clearChatHistory as clearStoredHistory,
  exportChatHistory,
  importChatHistory,
  loadChatHistory,
  saveChatHistory
} from '../utils/storage'
import { api } from '../utils/request'

export default {
  name: 'Chat',
  setup() {
    const inputQuery = ref('')
    const messages = ref([])
    const isLoading = ref(false)
    const isReindexing = ref(false)
    const apiStatus = ref('connecting')
    const healthInfo = ref({
      index_ready: false,
      index_status: 'connecting',
      index_error: '',
      history_count: 0,
      index_elapsed_seconds: 0,
      indexed_pdf_count: 0
    })
    const messagesContainer = ref(null)
    const fileInput = ref(null)
    const elapsedTime = ref(0)
    const activeConversationId = ref(null)
    const messageRefs = ref({})
    const toast = ref({ visible: false, message: '', type: 'info' })
    const dialog = ref({ visible: false, title: '', message: '', onConfirm: null })
    const isSidebarOpen = ref(true)
    const isMobile = ref(false)
    let timerInterval = null
    let healthTimer = null
    let toastTimer = null

    const syncViewportState = () => {
      isMobile.value = window.innerWidth <= 900
      if (isMobile.value) {
        isSidebarOpen.value = false
      } else {
        isSidebarOpen.value = true
      }
    }

    const toggleSidebar = () => {
      isSidebarOpen.value = !isSidebarOpen.value
    }

    const closeSidebar = () => {
      if (isMobile.value) isSidebarOpen.value = false
    }

    const showToast = (message, type = 'info') => {
      toast.value = { visible: true, message, type }
      if (toastTimer) clearTimeout(toastTimer)
      toastTimer = setTimeout(() => {
        toast.value.visible = false
      }, 2600)
    }

    const openDialog = (title, message, onConfirm) => {
      dialog.value = { visible: true, title, message, onConfirm }
    }

    const closeDialog = () => {
      dialog.value.visible = false
    }

    const confirmDialog = async () => {
      const action = dialog.value.onConfirm
      dialog.value.visible = false
      if (action) await action()
    }

    const canSend = computed(() => apiStatus.value === 'connected' && healthInfo.value.index_ready)

    const systemStatusTone = computed(() => {
      if (healthInfo.value.index_status === 'error' || apiStatus.value === 'error') return 'error'
      if (canSend.value) return 'ready'
      return 'warming'
    })

    const systemStatusLabel = computed(() => {
      if (systemStatusTone.value === 'ready') return 'Ready'
      if (systemStatusTone.value === 'error') return 'Error'
      return 'Building'
    })

    const systemHeadline = computed(() => {
      if (systemStatusTone.value === 'ready') return 'The index is ready. You can start asking questions now.'
      if (systemStatusTone.value === 'error') return healthInfo.value.index_error || 'The index or service is currently unavailable.'
      return 'The index is being built. Please wait a moment.'
    })

    const formattedIndexTimer = computed(() => {
      const total = Math.floor(healthInfo.value.index_elapsed_seconds || 0)
      const mins = String(Math.floor(total / 60)).padStart(2, '0')
      const secs = String(total % 60).padStart(2, '0')
      return `Elapsed ${mins}:${secs}`
    })

    const conversationItems = computed(() => {
      const items = []
      let order = 1

      for (let i = 0; i < messages.value.length; i += 1) {
        const userMessage = messages.value[i]
        const assistantMessage = messages.value[i + 1]
        if (!userMessage || userMessage.role !== 'user') continue

        items.push({
          id: `${i}-${order}`,
          title: summarize(userMessage.text, 18),
          preview: summarize(assistantMessage?.text || userMessage.text, 38),
          targetIndex: assistantMessage ? i + 1 : i
        })
        order += 1
      }

      return items.reverse()
    })

    const summarize = (text, limit) => {
      const value = String(text || '')
        .replace(/\s+/g, ' ')
        .replace(/[#*_`>\-\[\]]/g, '')
        .trim()
      return value.length > limit ? `${value.slice(0, limit)}...` : value
    }

    const truncate = (text, limit = 120) => {
      if (!text) return ''
      return text.length > limit ? `${text.slice(0, limit)}...` : text
    }

    const escapeHtml = (text) => String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')

    const applyInlineFormatting = (text) => {
      return escapeHtml(text)
        .replace(/\*\*([A-Za-z\u4e00-\u9fa5][^*:\n]{0,24}):\*\*/g, '<span class="answer-label">$1:</span>')
        .replace(/\*\*([A-Za-z\u4e00-\u9fa5][^*\n]{0,24})\*\*:/g, '<span class="answer-label">$1:</span>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        .replace(/\[(\d+)\]/g, '<sup class="citation">Ref $1</sup>')
    }

    const formatAnswer = (text) => {
      if (!text) return ''

      const blocks = text.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean)

      return blocks.map((block) => {
        if (block.startsWith('```') && block.endsWith('```')) {
          const code = block.slice(3, -3).trim()
          return `<pre><code>${escapeHtml(code)}</code></pre>`
        }

        if (/^#{1,6}\s+/.test(block)) {
          const headingText = block.replace(/^#{1,6}\s+/, '')
          return `<h3 class="answer-heading">${applyInlineFormatting(headingText)}</h3>`
        }

        const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
        const allListItems = lines.every((line) => /^[-*•]\s+/.test(line) || /^\d+\.\s+/.test(line))
        if (allListItems) {
          const listItems = lines.map((line) => {
            const content = line.replace(/^[-*•]\s+/, '').replace(/^\d+\.\s+/, '')
            return `<li>${applyInlineFormatting(content)}</li>`
          }).join('')
          return `<ul class="answer-list">${listItems}</ul>`
        }

        const paragraphHtml = lines.map((line) => applyInlineFormatting(line)).join('<br>')
        return `<p>${paragraphHtml}</p>`
      }).join('')
    }

    const registerMessageRef = (element, index) => {
      if (element) {
        messageRefs.value[index] = element
      } else {
        delete messageRefs.value[index]
      }
    }

    const jumpToConversation = async (item) => {
      activeConversationId.value = item.id
      await nextTick()
      messageRefs.value[item.targetIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      closeSidebar()
    }

    const scrollToBottom = async () => {
      await nextTick()
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }

    const startTimer = () => {
      elapsedTime.value = 0
      timerInterval = setInterval(() => {
        elapsedTime.value += 1
      }, 1000)
    }

    const stopTimer = () => {
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
    }

    const refreshHealth = async () => {
      try {
        const data = await api.health()
        healthInfo.value = data
        apiStatus.value = 'connected'
      } catch (error) {
        apiStatus.value = 'error'
        healthInfo.value = {
          ...healthInfo.value,
          index_ready: false,
          index_status: 'error',
          index_error: error.message || 'Health check failed'
        }
      }
    }

    const sendQuery = async () => {
      if (!inputQuery.value.trim() || isLoading.value || !canSend.value) return

      const query = inputQuery.value.trim()
      inputQuery.value = ''
      messages.value.push({ role: 'user', text: query })
      isLoading.value = true
      startTimer()
      await scrollToBottom()

      try {
        const data = await api.chat(query)
        messages.value.push({
          role: 'assistant',
          text: data.response,
          references: data.RAG_RESULT || data.rag_results || [],
          showReferences: false
        })
      } catch (error) {
        messages.value.push({
          role: 'assistant',
          text: `Request failed: ${error.message}`,
          references: [],
          showReferences: false
        })
        showToast(`Request failed: ${error.message}`, 'error')
      } finally {
        isLoading.value = false
        stopTimer()
        await refreshHealth()
        await scrollToBottom()
      }
    }

    const sendExampleQuery = (query) => {
      inputQuery.value = query
      sendQuery()
    }

    const reindex = async () => {
      isReindexing.value = true
      try {
        await api.reindex()
        await refreshHealth()
        showToast('Index rebuild started.', 'success')
      } catch (error) {
        showToast(`Index request failed: ${error.message}`, 'error')
      } finally {
        isReindexing.value = false
      }
    }

    const requestReindex = () => {
      openDialog('Rebuild index', 'The system will reprocess the PDFs and refresh the vector index. Continue?', reindex)
    }

    const clearHistory = async () => {
      try {
        await api.clearHistory()
        messages.value = []
        activeConversationId.value = null
        clearStoredHistory()
        showToast('The current conversation has been cleared.', 'success')
      } catch (error) {
        showToast(`Clear failed: ${error.message}`, 'error')
      }
    }

    const requestClearHistory = () => {
      openDialog('Start a new chat', 'Both the local and backend history will be cleared. Continue?', clearHistory)
    }

    const exportHistory = () => {
      exportChatHistory(messages.value)
      showToast('Chat history exported.', 'success')
    }

    const importHistory = () => {
      fileInput.value?.click()
    }

    const handleImport = async (event) => {
      const file = event.target.files?.[0]
      if (!file) return

      try {
        const importedMessages = await importChatHistory(file)
        messages.value = importedMessages
        await scrollToBottom()
        showToast('Chat history imported successfully.', 'success')
      } catch (error) {
        showToast(`Import failed: ${error.message}`, 'error')
      }

      event.target.value = ''
    }

    const logout = () => {
      localStorage.removeItem('user_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
    }

    const requestLogout = () => {
      openDialog('Sign out', 'You will return to the sign-in page. Exported files will not be removed. Continue?', logout)
    }

    const loadStoredHistory = () => {
      const stored = loadChatHistory()
      if (stored.length) messages.value = stored
    }

    watch(messages, (newMessages) => {
      saveChatHistory(newMessages)
    }, { deep: true })

    onMounted(async () => {
      syncViewportState()
      window.addEventListener('resize', syncViewportState)
      loadStoredHistory()
      await refreshHealth()
      await scrollToBottom()

      healthTimer = setInterval(() => {
        refreshHealth()
      }, 1000)
    })

    onBeforeUnmount(() => {
      stopTimer()
      if (healthTimer) clearInterval(healthTimer)
      if (toastTimer) clearTimeout(toastTimer)
      window.removeEventListener('resize', syncViewportState)
    })

    return {
      inputQuery,
      messages,
      isLoading,
      isReindexing,
      apiStatus,
      healthInfo,
      messagesContainer,
      fileInput,
      elapsedTime,
      activeConversationId,
      toast,
      dialog,
      isSidebarOpen,
      isMobile,
      canSend,
      systemStatusTone,
      systemStatusLabel,
      systemHeadline,
      formattedIndexTimer,
      conversationItems,
      truncate,
      formatAnswer,
      toggleSidebar,
      closeSidebar,
      sendQuery,
      sendExampleQuery,
      requestReindex,
      requestClearHistory,
      exportHistory,
      importHistory,
      handleImport,
      requestLogout,
      registerMessageRef,
      jumpToConversation,
      closeDialog,
      confirmDialog
    }
  }
}
</script>

<style scoped>
.chat-page {
  position: relative;
  height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background: #f7f7f8;
  color: #1f2937;
  overflow: hidden;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 14px 10px;
  background: #fbfbfc;
  border-right: 1px solid #eceff3;
  overflow: hidden;
  min-height: 0;
}

.sidebar-header {
  display: flex;
  gap: 8px;
}

.sidebar-primary,
.sidebar-close,
.ghost-icon-btn,
.quiet-btn,
.reference-toggle,
.dialog-btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #1f2937;
  cursor: pointer;
}

.sidebar-primary {
  width: 100%;
  height: 40px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.sidebar-close {
  padding: 0 12px;
  border-radius: 12px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.brand-badge {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #111827;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.sidebar-brand strong {
  display: block;
  font-size: 14px;
}

.sidebar-brand p {
  margin: 3px 0 0;
  color: #9aa3b2;
  font-size: 12px;
}

.sidebar-group {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sidebar-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  margin-bottom: 8px;
}

.sidebar-label {
  font-size: 12px;
  color: #9aa3b2;
}

.sidebar-count,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

.sidebar-count {
  background: #f2f4f7;
  color: #6b7280;
}

.status-ready {
  color: #166534;
  background: #ecfdf3;
}

.status-warming {
  color: #92400e;
  background: #fff7ed;
}

.status-error {
  color: #b91c1c;
  background: #fef2f2;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: auto;
  min-height: 0;
  padding-right: 4px;
}

.conversation-item {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
}

.conversation-item:hover,
.conversation-item.active {
  background: #ffffff;
  border-color: #eceff3;
}

.conversation-item strong,
.conversation-item p {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.conversation-item strong {
  font-size: 13px;
  font-weight: 500;
}

.conversation-item p,
.conversation-empty,
.status-copy {
  color: #8b95a7;
  font-size: 12px;
  line-height: 1.7;
}

.conversation-item p {
  margin-top: 4px;
}

.conversation-empty {
  padding: 0 12px;
}

.sidebar-status {
  margin-top: auto;
  padding: 10px 12px 0;
  border-top: 1px solid #eceff3;
}

.status-copy {
  margin: 6px 0 0;
}

.status-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.status-meta span {
  padding: 5px 9px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
}

.main-shell {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background: #ffffff;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid #eceff3;
  background: rgba(255, 255, 255, 0.92);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ghost-icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  font-size: 15px;
  line-height: 1;
}

.topbar-title {
  font-size: 15px;
  font-weight: 600;
}

.topbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quiet-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  font-size: 12px;
}

.chat-shell {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
}

.messages-panel {
  min-height: 0;
  height: 100%;
  overflow: auto;
  padding: 18px 18px 10px;
  scrollbar-gutter: stable;
  overscroll-behavior: contain;
}

.empty-chat-state {
  max-width: 700px;
  margin: 44px auto 0;
  padding: 0 6px;
  text-align: center;
}

.empty-chat-state h2 {
  margin: 0 0 10px;
  font-size: clamp(26px, 4vw, 36px);
  line-height: 1.16;
  color: #111827;
  letter-spacing: -0.03em;
}

.empty-chat-state p {
  margin: 0 auto;
  max-width: 540px;
  color: #8b95a7;
  font-size: 15px;
  line-height: 1.85;
}

.starter-list {
  margin-top: 22px;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
}

.starter-btn {
  height: 40px;
  padding: 0 16px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
}

.message-row {
  max-width: 760px;
  margin: 0 auto 18px;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
}

.message-row.user {
  grid-template-columns: minmax(0, 1fr) 36px;
}

.avatar {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}

.avatar-agent {
  background: #111827;
  color: #ffffff;
  border-color: #111827;
}

.avatar-user {
  background: linear-gradient(135deg, #86efac 0%, #34d399 100%);
  color: #ffffff;
  border-color: #6ee7b7;
  box-shadow: 0 6px 14px rgba(52, 211, 153, 0.22);
}

.message-row.user .avatar {
  order: 2;
}

.message-row.user .message-block {
  order: 1;
}

.message-block {
  min-width: 0;
  max-width: min(720px, 100%);
}

.message-row.user .message-block {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  padding: 0 2px;
}

.message-row.user .message-meta {
  justify-content: flex-end;
}

.message-meta strong {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.message-row.user .message-meta strong {
  color: #155e3b;
}

.assistant-bubble,
.user-bubble {
  border: 1px solid #eceff3;
  border-radius: 18px;
  padding: 15px 18px;
  box-shadow: 0 8px 26px rgba(17, 24, 39, 0.035);
  overflow-wrap: anywhere;
}

.assistant-bubble {
  background: #ffffff;
  border-top-left-radius: 8px;
  max-width: min(680px, 100%);
}

.user-bubble {
  background: #d9fdd3;
  border-color: #c7efc0;
  border-top-right-radius: 8px;
  max-width: min(560px, 100%);
  color: #183226;
  box-shadow: 0 6px 18px rgba(24, 50, 38, 0.06);
  position: relative;
}

.user-bubble::after {
  content: "";
  position: absolute;
  top: 10px;
  right: -6px;
  width: 12px;
  height: 12px;
  background: #d9fdd3;
  border-top: 1px solid #c7efc0;
  border-right: 1px solid #c7efc0;
  transform: rotate(45deg);
}

.loading-bubble {
  display: flex;
  align-items: center;
  gap: 12px;
}

.loading-dots {
  display: inline-flex;
  gap: 6px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #9ca3af;
  animation: blink 1s infinite ease-in-out;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.15s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.3s;
}

.reference-panel {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #eef1f4;
}

.reference-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12px;
  color: #556274;
  background: #f8fafc;
  border: 1px solid #e8edf3;
}

.reference-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: #eef2f7;
  color: #526071;
  font-size: 11px;
}

.reference-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.reference-preview-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.reference-preview-item {
  display: grid;
  gap: 5px;
  padding: 11px 13px;
  border: 1px solid #edf1f5;
  border-radius: 14px;
  background: #fbfcfe;
}

.reference-preview-item strong {
  font-size: 12px;
  color: #334155;
  font-weight: 600;
}

.reference-preview-item span {
  font-size: 11px;
  color: #8b95a7;
}

.reference-preview-item p {
  margin: 0;
  font-size: 12px;
  line-height: 1.75;
  color: #607083;
}

.reference-item {
  padding: 13px 14px;
  border: 1px solid #edf1f5;
  border-radius: 16px;
  background: #fbfcfe;
}

.reference-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 11px;
  color: #6b7280;
}

.reference-item p {
  margin: 0;
  color: #556274;
  font-size: 12px;
  line-height: 1.75;
}

.reference-content :deep(p) {
  margin: 0 0 10px;
  color: #556274;
  font-size: 13px;
  line-height: 1.78;
  letter-spacing: 0.002em;
}

.reference-content :deep(p:last-child) {
  margin-bottom: 0;
}

.reference-content :deep(.answer-heading) {
  margin: 4px 0 8px;
  font-size: 14px;
  line-height: 1.55;
  font-weight: 600;
  color: #334155;
}

.reference-content :deep(.answer-list) {
  margin: 8px 0 10px 17px;
  font-size: 13px;
  line-height: 1.72;
}

.reference-content :deep(strong) {
  font-weight: 600;
  color: #334155;
}

.reference-content :deep(.answer-label) {
  display: inline;
  color: #475569;
  font-weight: 600;
}

.composer-shell {
  padding: 12px 18px 18px;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #ffffff 22%, #ffffff 100%);
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.composer-box {
  max-width: 760px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 96px;
  gap: 10px;
  align-items: end;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08), 0 2px 10px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(12px);
}

.composer-input {
  min-height: 92px;
  resize: none;
  padding: 14px;
  border: none;
  border-radius: 16px;
  background: transparent;
  color: #111827;
  font: inherit;
  outline: none;
}

.composer-input:focus {
  background: #fafafa;
}

.send-btn {
  height: 52px;
  border: none;
  border-radius: 16px;
  background: #111827;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  align-self: end;
}

.send-btn:disabled,
.quiet-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.hidden-input {
  display: none;
}

.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 20;
  padding: 12px 16px;
  border-radius: 14px;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 16px 40px rgba(29, 41, 73, 0.18);
}

.toast-info {
  background: #3b82f6;
}

.toast-success {
  background: #16a34a;
}

.toast-error {
  background: #dc2626;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 25;
  background: rgba(15, 23, 42, 0.22);
  display: grid;
  place-items: center;
  padding: 20px;
}

.dialog-card {
  width: min(420px, 100%);
  padding: 24px;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(17, 24, 39, 0.12);
}

.dialog-card h3 {
  margin: 0 0 10px;
  font-size: 22px;
  color: #111827;
}

.dialog-card p {
  margin: 0;
  color: #6b7280;
  line-height: 1.75;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.dialog-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 14px;
}

.dialog-btn.solid {
  border: none;
  background: #111827;
  color: #fff;
}

.answer-content :deep(p) {
  margin: 0 0 16px;
  line-height: 1.9;
  color: #27303f;
  font-size: 15px;
  font-weight: 400;
  letter-spacing: 0.003em;
  word-break: break-word;
}

.answer-content :deep(p:last-child) {
  margin-bottom: 0;
}

.answer-content :deep(.answer-heading) {
  margin: 10px 0 12px;
  color: #111827;
  font-size: 16px;
  line-height: 1.55;
  font-weight: 600;
  letter-spacing: -0.012em;
}

.answer-content :deep(.answer-list) {
  margin: 8px 0 16px 18px;
  color: #27303f;
  line-height: 1.82;
  font-size: 15px;
  padding-left: 4px;
}

.answer-content :deep(.answer-list li) {
  margin-bottom: 10px;
}

.answer-content :deep(.answer-list li:last-child) {
  margin-bottom: 0;
}

.answer-content :deep(.citation) {
  display: inline-flex;
  align-items: center;
  margin: 0 4px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #f6f8fb;
  color: #637186;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid #e7edf4;
  vertical-align: baseline;
}

.answer-content :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.answer-content :deep(em) {
  color: #4b5563;
  font-style: italic;
}

.answer-content :deep(.answer-label) {
  display: inline;
  color: #667085;
  font-weight: 600;
}

.answer-content :deep(.inline-code),
.answer-content :deep(pre) {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.answer-content :deep(.inline-code) {
  padding: 2px 7px;
  font-size: 12px;
  color: #334155;
}

.answer-content :deep(pre) {
  margin: 10px 0 16px;
  padding: 14px 16px;
  overflow: auto;
  line-height: 1.72;
  font-size: 13px;
  color: #233041;
}


.conversation-list::-webkit-scrollbar,
.messages-panel::-webkit-scrollbar {
  width: 12px;
}

.conversation-list::-webkit-scrollbar-thumb,
.messages-panel::-webkit-scrollbar-thumb {
  background: #cfd6e3;
  border-radius: 999px;
  border: 3px solid #ffffff;
}

.conversation-list::-webkit-scrollbar-track,
.messages-panel::-webkit-scrollbar-track {
  background: transparent;
}

.mobile-mask {
  position: fixed;
  inset: 0;
  z-index: 9;
  background: rgba(15, 23, 42, 0.18);
}

.toast-enter-active,
.toast-leave-active,
.modal-enter-active,
.modal-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to,
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@keyframes blink {
  0%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

@media (max-width: 900px) {
  .chat-page {
    grid-template-columns: 1fr;
  }

  .sidebar.mobile {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 12;
    width: min(280px, 84vw);
    transform: translateX(-100%);
    transition: transform 0.22s ease;
    box-shadow: 8px 0 32px rgba(17, 24, 39, 0.08);
  }

  .sidebar.mobile.open {
    transform: translateX(0);
  }
}

@media (max-width: 720px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .topbar-actions {
    width: 100%;
  }

  .composer-box {
    grid-template-columns: 1fr;
  }

  .send-btn {
    height: 48px;
  }
}
</style>
