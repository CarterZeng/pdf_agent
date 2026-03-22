<template>
  <div class="login-container">
    <!-- 动态背景 -->
    <div class="background-gradient"></div>
    <div class="floating-particles">
      <div v-for="i in 20" :key="i" class="particle" :style="{ '--delay': `${i * 0.1}s` }"></div>
    </div>

    <!-- 登录内容 -->
    <div class="login-content">
      <!-- 左侧装饰 -->
      <div class="left-section">
        <div class="rotating-icon-wrapper">
          <!-- Logo - 移除雷达动态效果，只保留logo -->
          <div class="logo-badge">
            <div class="logo-inner">
              <img src="@/assets/school-logo.png" alt="学校 Logo" class="logo-img">
            </div>
          </div>
        </div>

        <h1>PDF Agent</h1>
        <p class="subtitle">智能学术 RAG 系统</p>
        
        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-icon">🔍</span>
            <span>精准检索</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📚</span>
            <span>学术资源</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">⚡</span>
            <span>极速响应</span>
          </div>
        </div>

        <!-- 装饰线条 -->
        <div class="decoration-line"></div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="right-section">
        <div class="form-container">
          <div class="form-header">
            <h2>欢迎使用</h2>
            <p>开始探索知识的奥秘</p>
          </div>

          <form @submit.prevent="handleLogin" class="login-form">
            <!-- 用户名 -->
            <div class="form-group">
              <label>用户名</label>
              <div class="input-wrapper" :class="{ focused: focusedField === 'username' }">
                <span class="input-icon">👤</span>
                <input
                  v-model="username"
                  type="text"
                  placeholder="输入用户名或邮箱"
                  @focus="focusedField = 'username'"
                  @blur="focusedField = null"
                >
              </div>
              <span v-if="errors.username" class="error-text">{{ errors.username }}</span>
            </div>

            <!-- 密码 -->
            <div class="form-group">
              <label>密码</label>
              <div class="input-wrapper" :class="{ focused: focusedField === 'password' }">
                <span class="input-icon">🔐</span>
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="输入密码"
                  @focus="focusedField = 'password'"
                  @blur="focusedField = null"
                  @keydown.enter="handleLogin"
                >
                <button
                  type="button"
                  class="password-toggle"
                  @click.prevent="showPassword = !showPassword"
                  :title="showPassword ? '隐藏' : '显示'"
                >
                  {{ showPassword ? '👁️' : '👁️‍🗨️' }}
                </button>
              </div>
              <span v-if="errors.password" class="error-text">{{ errors.password }}</span>
            </div>

            <!-- 记住我 & 忘记密码 -->
            <div class="form-options">
              <label class="checkbox-label">
                <input v-model="rememberMe" type="checkbox">
                <span>记住我</span>
              </label>
              <a href="#" class="forgot-link" @click.prevent="showForgotPassword">忘记密码？</a>
            </div>

            <!-- 登录按钮 -->
            <button type="submit" class="login-btn" :disabled="isLoading">
              <span v-if="!isLoading" class="btn-content">
                <span class="btn-text">开始使用</span>
                <span class="btn-arrow">→</span>
              </span>
              <span v-else class="loading-spinner">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </button>

            <!-- 重构分割线+快速登录：按钮放在“或”字两侧 -->
            <div class="quick-login-wrapper">
              <button type="button" class="quick-btn wechat" @click.prevent="quickLogin('wechat')">
                <img class="quick-icon-img" src="@/assets/wechat.png" alt="微信图标">
                <span>微信</span>
              </button>
              <div class="divider-text">或</div>
              <button type="button" class="quick-btn qq" @click.prevent="quickLogin('qq')">
                <img class="quick-icon-img" src="@/assets/qq.png" alt="QQ图标">
                <span>QQ</span>
              </button>
            </div>

            <!-- 注册链接 -->
            <div class="register-link">
              没有账号？<a href="#" @click.prevent="goToRegister">立即注册</a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <transition name="toast">
      <div v-if="errorMessage" class="error-toast">
        <span class="toast-icon">❌</span>
        <span class="toast-text">{{ errorMessage }}</span>
      </div>
    </transition>

    <!-- 成功提示 -->
    <transition name="toast">
      <div v-if="successMessage" class="success-toast">
        <span class="toast-icon">✅</span>
        <span class="toast-text">{{ successMessage }}</span>
      </div>
    </transition>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const showPassword = ref(false)
    const rememberMe = ref(true)
    const focusedField = ref(null)
    const isLoading = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')
    const errors = ref({ username: '', password: '' })

    const validateForm = () => {
      errors.value = { username: '', password: '' }
      let isValid = true

      if (!username.value.trim()) {
        errors.value.username = '请输入用户名'
        isValid = false
      }
      if (!password.value.trim()) {
        errors.value.password = '请输入密码'
        isValid = false
      } else if (password.value.length < 6) {
        errors.value.password = '密码至少6位'
        isValid = false
      }

      return isValid
    }

    const handleLogin = async () => {
      if (!validateForm()) return

      isLoading.value = true
      errorMessage.value = ''

      try {
        await new Promise(resolve => setTimeout(resolve, 1500))

        if (username.value === 'admin1' && password.value === 'admin1') {
          successMessage.value = '登录成功，跳转中...'
          localStorage.setItem('user_token', 'token_' + Date.now())
          localStorage.setItem('user_info', JSON.stringify({ 
            username: username.value,
            loginTime: new Date().toISOString()
          }))
          
          if (rememberMe.value) {
            localStorage.setItem('remembered_username', username.value)
          }

          setTimeout(() => {
            router.push('/')
          }, 1000)
        } else {
          showError('用户名或密码错误（试试 admin1/admin1）')
        }
      } catch (error) {
        showError('登录失败，请重试')
        console.error('Login error:', error)
      } finally {
        isLoading.value = false
      }
    }

    const quickLogin = (type) => {
      const typeText = type === 'wechat' ? '微信' : 'QQ'
      successMessage.value = `正在通过 ${typeText} 登录...`
      setTimeout(() => {
        router.push('/')
      }, 1500)
    }

    const goToRegister = () => {
      router.push('/register')
    }

    const showForgotPassword = () => {
      alert('密码重置功能即将上线，敬请期待')
    }

    const showError = (message) => {
      errorMessage.value = message
      setTimeout(() => {
        errorMessage.value = ''
      }, 4000)
    }

    if (localStorage.getItem('remembered_username')) {
      username.value = localStorage.getItem('remembered_username')
    }

    return {
      username,
      password,
      showPassword,
      rememberMe,
      focusedField,
      isLoading,
      errorMessage,
      successMessage,
      errors,
      handleLogin,
      quickLogin,
      goToRegister,
      showForgotPassword
    }
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 淡色系主题调整 */
:root {
  --primary: #9abfff;
  --primary-light: #e0e9ff; /* 更浅的主色，与背景区分 */
  --primary-dark: #7aa0e8;
  --bg-light: #fafbff;
  --text-primary: #2d3748;
  --text-secondary: #718096;
  --border: #e8f0fe;
  --shadow: 0 8px 32px rgba(154, 191, 255, 0.15);
  --btn-bg: #f0f7ff; /* 登录按钮浅色系背景 */
}

.login-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
  position: relative;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

.background-gradient {
  position: absolute;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    45deg,
    #f0f7ff 0%,
    #e8f4f8 25%,
    #fef7fb 50%,
    #f5fafe 75%,
    #f0f7ff 100%
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
  top: -50%;
  left: -50%;
  z-index: 0;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.floating-particles {
  position: absolute;
  width: 100%;
  height: 100%;
  overflow: hidden;
  z-index: 1;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(154, 191, 255, 0.6);
  border-radius: 50%;
  animation: float 20s infinite ease-in-out;
  animation-delay: var(--delay);
  left: 10%;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) translateX(100px);
    opacity: 0;
  }
}

.login-content {
  display: flex;
  width: 100%;
  max-width: 1300px;
  background: white;
  border-radius: 24px;
  box-shadow: 0 25px 50px rgba(154, 191, 255, 0.2);
  overflow: hidden;
  z-index: 10;
  position: relative;
}

.left-section {
  flex: 1;
  padding: 80px 60px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 40px;
  position: relative;
  overflow: hidden;
}

.rotating-icon-wrapper {
  position: relative;
  width: 160px;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-badge {
  position: relative;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  background: white;
  border-radius: 20px;
  box-shadow: 0 12px 32px rgba(154, 191, 255, 0.2);
  animation: pulseScale 3s ease-in-out infinite;
}

.logo-inner {
  width: 90px;
  height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(154, 191, 255, 0.1));
}

@keyframes pulseScale {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.left-section h1 {
  font-size: 42px;
  font-weight: 800;
  margin: 0;
  text-align: center;
  letter-spacing: -1px;
  color: var(--primary-dark);
}

.left-section .subtitle {
  font-size: 16px;
  opacity: 0.95;
  text-align: center;
  margin: 0;
  font-weight: 300;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
}

.feature-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(154, 191, 255, 0.2);
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: translateX(8px);
  border-color: rgba(154, 191, 255, 0.4);
}

.feature-icon {
  font-size: 22px;
  flex-shrink: 0;
  color: var(--primary-dark);
}

.decoration-line {
  width: 60px;
  height: 3px;
  background: rgba(154, 191, 255, 0.4);
  border-radius: 2px;
  margin-top: 20px;
}

.right-section {
  flex: 1;
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 400px;
}

.form-header {
  margin-bottom: 48px;
  text-align: center;
}

.form-header h2 {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: -0.5px;
  color: var(--primary-dark);
}

.form-header p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  font-weight: 400;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.3px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 15px;
  border: 2px solid var(--border);
  border-radius: 12px;
  background: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.input-wrapper.focused {
  border-color: var(--primary);
  box-shadow: 0 0 0 4px rgba(154, 191, 255, 0.1);
  background: rgba(154, 191, 255, 0.05);
}

.input-icon {
  font-size: 18px;
  flex-shrink: 0;
  opacity: 0.8;
  color: var(--primary-dark);
}

.input-wrapper input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--text-primary);
  background: transparent;
  font-weight: 500;
}

.input-wrapper input::placeholder {
  color: #c0c8d0;
  font-weight: 400;
}

.password-toggle {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 6px 10px;
  transition: all 0.3s ease;
  flex-shrink: 0;
  color: var(--primary-dark);
}

.password-toggle:hover {
  transform: scale(1.15);
}

.error-text {
  font-size: 12px;
  color: #ff8a8a;
  margin-top: -4px;
  font-weight: 500;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  margin: 4px 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  color: var(--text-primary);
  font-weight: 500;
  transition: all 0.3s ease;
}

.checkbox-label:hover {
  color: var(--primary);
}

.checkbox-label input {
  cursor: pointer;
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.forgot-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.forgot-link:hover {
  color: var(--primary-dark);
  text-decoration: underline;
}

/* 登录按钮样式调整：浅色系背景 + 强制黑色字体 */
.login-btn {
  padding: 15px 22px;
  background: linear-gradient(135deg, var(--btn-bg) 0%, var(--primary-light) 100%);
  color: #000 !important; /* 强制黑色字体 */
  border: 1px solid rgba(154, 191, 255, 0.3); /* 增加边框强化区分度 */
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 50px;
  letter-spacing: 0.5px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 16px 40px rgba(154, 191, 255, 0.3);
  background: linear-gradient(135deg, #e8f0fe 0%, #d0e0ff 100%); /* hover时略加深 */
}

.login-btn:active:not(:disabled) {
  transform: translateY(-1px);
}

.login-btn:disabled {
  opacity: 0.85;
  cursor: not-allowed;
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-arrow {
  font-size: 18px;
  animation: slideArrow 1s infinite;
  color: #000 !important; /* 箭头也强制黑色 */
}

@keyframes slideArrow {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(4px); }
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 20px;
}

.loading-spinner span {
  width: 5px;
  height: 5px;
  background: #000; /* 加载动画改为黑色，匹配按钮字体 */
  border-radius: 50%;
  animation: loadingBounce 1.4s infinite;
}

.loading-spinner span:nth-child(2) { animation-delay: 0.2s; }
.loading-spinner span:nth-child(3) { animation-delay: 0.4s; }

@keyframes loadingBounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.2); opacity: 1; }
}

/* 重构快速登录区域：按钮在“或”字两侧 */
.quick-login-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 0;
  width: 100%;
}

/* “或”字样式 */
.divider-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
  padding: 0 10px;
  white-space: nowrap;
}

/* 快速登录按钮样式 */
.quick-btn {
  flex: 1;
  padding: 12px 8px;
  border: 2px solid var(--border);
  border-radius: 12px;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--text-primary);
  /* 确保按钮不被挤压 */
  min-width: 120px;
}

.quick-btn:hover {
  border-color: var(--primary);
  background: rgba(154, 191, 255, 0.08);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(154, 191, 255, 0.15);
}

/* 图标样式：隔离+放大，优先级最高 */
.quick-icon-img {
  width: 28px !important; /* 放大图标到28px */
  height: 28px !important;
  object-fit: contain !important;
  flex-shrink: 0 !important;
  /* 重置所有可能影响的样式，确保纯净 */
  filter: none !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 微信/QQ按钮单独样式（仅文字颜色，不影响图标） */
.quick-btn.wechat {
  color: #07c160;
}

.quick-btn.qq {
  color: #12b7f5;
}

.register-link {
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 24px;
  font-weight: 500;
}

.register-link a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 700;
  transition: all 0.3s ease;
  margin-left: 4px;
}

.register-link a:hover {
  color: var(--primary-dark);
  text-decoration: underline;
}

.error-toast,
.success-toast {
  position: fixed;
  bottom: 30px;
  right: 30px;
  padding: 14px 22px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 1000;
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 32px rgba(154, 191, 255, 0.2);
}

.error-toast {
  background: rgba(255, 138, 138, 0.95);
  color: white;
  border: 1px solid rgba(255, 138, 138, 0.8);
}

.success-toast {
  background: rgba(145, 213, 120, 0.95);
  color: white;
  border: 1px solid rgba(145, 213, 120, 0.8);
}

.toast-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.toast-text {
  flex: 1;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
  transform: translateY(20px) translateX(10px);
  opacity: 0;
}

/* 响应式调整 */
@media (max-width: 1024px) {
  .login-content {
    flex-direction: column;
    max-width: 95%;
  }

  .left-section {
    padding: 50px 40px;
    gap: 30px;
  }

  .right-section {
    padding: 50px 40px;
  }

  .feature-list {
    flex-direction: row;
    gap: 12px;
  }

  .feature-item {
    flex: 1;
    padding: 10px 12px;
    font-size: 12px;
  }

  .left-section h1 {
    font-size: 32px;
  }
}

@media (max-width: 768px) {
  .login-container {
    padding: 20px;
  }

  .login-content {
    border-radius: 16px;
  }

  .left-section {
    padding: 40px 20px;
    gap: 25px;
  }

  .rotating-icon-wrapper {
    width: 120px;
    height: 120px;
  }

  .logo-badge {
    width: 100px;
    height: 100px;
  }

  .logo-inner {
    width: 70px;
    height: 70px;
  }

  .left-section h1 {
    font-size: 26px;
  }

  .right-section {
    padding: 40px 20px;
  }

  .form-container {
    max-width: 100%;
  }

  .form-header h2 {
    font-size: 24px;
  }

  /* 响应式下快速登录按钮适配 */
  .quick-btn {
    min-width: 100px;
    padding: 10px 4px;
    font-size: 13px;
  }
  
  .quick-icon-img {
    width: 24px !important;
    height: 24px !important;
  }
}

@media (max-width: 600px) {
  .login-container {
    padding: 10px;
  }

  .left-section {
    padding: 30px 15px;
  }

  .right-section {
    padding: 30px 15px;
  }

  .form-header h2 {
    font-size: 20px;
  }

  .login-form {
    gap: 16px;
  }

  .error-toast,
  .success-toast {
    bottom: 20px;
    right: 20px;
    left: 20px;
    width: auto;
  }

  /* 小屏下快速登录按钮堆叠 */
  .quick-login-wrapper {
    flex-direction: column;
    gap: 10px;
  }
  
  .quick-btn {
    width: 100%;
    min-width: unset;
  }
  
  .divider-text {
    padding: 10px 0;
  }
}
</style>