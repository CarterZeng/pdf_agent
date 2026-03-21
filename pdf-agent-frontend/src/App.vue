<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-content">
        <h1>PDF智能问答助手</h1>
        <el-button 
          type="primary" 
          icon="el-icon-refresh" 
          @click="handleReindex"
          :loading="reindexLoading"
        >
          重新构建PDF索引
        </el-button>
      </div>
    </el-header>

    <!-- 主体内容 -->
    <el-container class="main-container">
      <!-- 聊天记录区域 -->
      <el-main class="chat-container">
        <div class="chat-history" ref="chatHistoryRef">
          <!-- 系统提示 -->
          <div class="message-item system">
            <div class="message-content">
              欢迎使用PDF智能问答助手！请先确保./pdfs目录下有PDF文件，首次使用请点击"重新构建PDF索引"。
            </div>
          </div>

          <!-- 对话历史 -->
          <div 
            v-for="(item, index) in chatHistory" 
            :key="index" 
            :class="['message-item', item.role]"
          >
            <div class="message-avatar">
              <el-avatar :icon="item.role === 'user' ? 'el-icon-user' : 'el-icon-s-tools'">
                {{ item.role === 'user' ? '用户' : '助手' }}
              </el-avatar>
            </div>
            <div class="message-content">
              <!-- 用户消息 -->
              <div v-if="item.role === 'user'" class="user-message">
                {{ item.content }}
              </div>

              <!-- 助手消息 -->
              <div v-if="item.role === 'assistant'" class="assistant-message">
                <!-- 回答内容 -->
                <div class="answer-content" v-html="item.response"></div>
                
                <!-- RAG检索结果 -->
                <div v-if="item.RAG_RESULT && item.RAG_RESULT.length" class="rag-result">
                  <h4>📚 检索到的参考内容：</h4>
                  <el-collapse>
                    <el-collapse-item 
                      v-for="(rag, ragIndex) in item.RAG_RESULT" 
                      :key="ragIndex" 
                      :title="`[${rag.ref_id}] ${rag.source} - 第${rag.page}页`"
                    >
                      <pre class="rag-content">{{ rag.content }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </div>
          </div>

          <!-- 加载中提示 -->
          <div v-if="loading" class="message-item loading">
            <el-skeleton :rows="3" animated />
          </div>
        </div>
      </el-main>

      <!-- 输入区域 -->
      <el-footer class="input-footer">
        <el-input
          v-model="inputPrompt"
          type="textarea"
          placeholder="请输入您的问题..."
          :rows="3"
          @keyup.enter="handleSend"
          class="input-box"
        />
        <el-button 
          type="primary" 
          icon="el-icon-send" 
          @click="handleSend"
          :disabled="!inputPrompt.trim() || loading"
          class="send-btn"
        >
          发送
        </el-button>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from './utils/request'

// 响应式数据
const inputPrompt = ref('')
const chatHistory = ref([])
const loading = ref(false)
const reindexLoading = ref(false)
const chatHistoryRef = ref(null)

// 监听聊天记录变化，自动滚动到底部
watch(chatHistory, () => {
  nextTick(() => {
    if (chatHistoryRef.value) {
      chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
    }
  })
}, { deep: true })

// 发送消息
const handleSend = async () => {
  const prompt = inputPrompt.value.trim()
  if (!prompt || loading.value) return

  // 添加用户消息到历史
  chatHistory.value.push({
    role: 'user',
    content: prompt
  })
  inputPrompt.value = ''
  loading.value = true

  try {
    // 调用后端聊天接口
    const res = await api.chat(prompt)
    // 添加助手消息到历史
    chatHistory.value.push({
      role: 'assistant',
      response: res.response,
      RAG_RESULT: res.RAG_RESULT
    })
  } catch (error) {
    ElMessage.error('问答失败，请重试')
  } finally {
    loading.value = false
  }
}

// 重新构建索引
const handleReindex = async () => {
  try {
    await ElMessageBox.confirm(
      '重新构建索引会重新解析所有PDF文件，是否确认？',
      '提示',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    reindexLoading.value = true
    await api.reindex()
    ElMessage.success('索引构建成功！')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('索引构建失败，请重试')
    }
  } finally {
    reindexLoading.value = false
  }
}

// 页面挂载后滚动到底部
onMounted(() => {
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.header {
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
}

.main-container {
  flex: 1;
  padding: 20px;
  overflow: hidden;
}

.chat-container {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  height: 100%;
  overflow: hidden;
}

.chat-history {
  height: 100%;
  overflow-y: auto;
  padding-right: 10px;
}

.message-item {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message-item.system {
  justify-content: center;
}

.message-item.system .message-content {
  background-color: #e8f4f8;
  color: #4299e1;
  max-width: 80%;
  text-align: center;
}

.message-item.user {
  justify-content: flex-end;
}

.message-item.assistant {
  justify-content: flex-start;
}

.message-avatar {
  margin-right: 10px;
  margin-left: 10px;
}

.message-content {
  background-color: #f0f2f5;
  border-radius: 8px;
  padding: 10px 15px;
  max-width: 70%;
  word-wrap: break-word;
}

.user-message {
  background-color: #409eff;
  color: #fff;
  border-radius: 8px;
  padding: 10px;
}

.assistant-message {
  line-height: 1.6;
}

.rag-result {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #e6e6e6;
}

.rag-content {
  white-space: pre-wrap;
  word-break: break-all;
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
}

.input-footer {
  margin-top: 20px;
  background-color: #fff;
  padding: 15px;
  border-radius: 8px;
  display: flex;
  gap: 10px;
}

.input-box {
  flex: 1;
}

.send-btn {
  width: 100px;
}

.loading {
  justify-content: center;
}

/* 滚动条样式优化 */
.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-thumb {
  background-color: #dcdfe6;
  border-radius: 3px;
}
</style>