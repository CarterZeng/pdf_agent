<template>
  <div class="login-page">
    <section class="login-card">
      <div class="card-header">
        <div class="logo-box">
          <img src="@/assets/school-logo.png" alt="学校 Logo" class="logo-img">
        </div>
        <div>
          <p class="card-eyebrow">PDF Agent</p>
          <h2>登录研究控制台</h2>
        </div>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <label class="field-group">
          <span>用户名</span>
          <input
            v-model="username"
            type="text"
            placeholder="输入用户名"
            autocomplete="username"
          >
          <small v-if="errors.username" class="error-text">{{ errors.username }}</small>
        </label>

        <label class="field-group">
          <span>密码</span>
          <div class="password-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="输入密码"
              autocomplete="current-password"
            >
            <button type="button" class="toggle-btn" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
          <small v-if="errors.password" class="error-text">{{ errors.password }}</small>
        </label>

        <div class="login-row">
          <label class="remember-row">
            <input v-model="rememberMe" type="checkbox">
            <span>记住账号</span>
          </label>
          <span class="helper-text">测试账号：admin1 / admin1</span>
        </div>

        <button class="submit-btn" type="submit" :disabled="isLoading">
          {{ isLoading ? '正在登录...' : '进入系统' }}
        </button>
      </form>

      <div class="channel-divider">
        <span>其他登录方式</span>
      </div>

      <div class="channel-row">
        <button class="channel-btn" type="button" @click="handleChannelLogin('qq')">
          <img src="@/assets/qq.png" alt="QQ" class="channel-icon">
          <span>QQ 登录</span>
        </button>
        <button class="channel-btn" type="button" @click="handleChannelLogin('wechat')">
          <img src="@/assets/wechat.png" alt="微信" class="channel-icon">
          <span>微信登录</span>
        </button>
      </div>
    </section>

    <transition name="toast">
      <div v-if="toast.visible" :class="['toast', `toast-${toast.type}`]">
        {{ toast.message }}
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
    const username = ref(localStorage.getItem('remembered_username') || '')
    const password = ref('')
    const rememberMe = ref(true)
    const showPassword = ref(false)
    const isLoading = ref(false)
    const errors = ref({ username: '', password: '' })
    const toast = ref({ visible: false, message: '', type: 'info' })
    let toastTimer = null

    const showToast = (message, type = 'info') => {
      toast.value = { visible: true, message, type }
      if (toastTimer) clearTimeout(toastTimer)
      toastTimer = setTimeout(() => {
        toast.value.visible = false
      }, 2800)
    }

    const completeLogin = (name) => {
      localStorage.setItem('user_token', `token_${Date.now()}`)
      localStorage.setItem('user_info', JSON.stringify({
        username: name,
        loginTime: new Date().toISOString()
      }))
      router.push('/')
    }

    const validateForm = () => {
      errors.value = { username: '', password: '' }
      let valid = true

      if (!username.value.trim()) {
        errors.value.username = '请输入用户名'
        valid = false
      }

      if (!password.value.trim()) {
        errors.value.password = '请输入密码'
        valid = false
      } else if (password.value.length < 6) {
        errors.value.password = '密码至少 6 位'
        valid = false
      }

      return valid
    }

    const handleLogin = async () => {
      if (!validateForm()) return

      isLoading.value = true
      try {
        await new Promise((resolve) => setTimeout(resolve, 700))

        if (username.value === 'admin1' && password.value === 'admin1') {
          if (rememberMe.value) {
            localStorage.setItem('remembered_username', username.value)
          } else {
            localStorage.removeItem('remembered_username')
          }

          showToast('登录成功，正在进入工作台', 'success')
          setTimeout(() => {
            completeLogin(username.value)
          }, 500)
        } else {
          showToast('用户名或密码错误，请使用 admin1 / admin1', 'error')
        }
      } catch (error) {
        console.error('Login error:', error)
        showToast('登录失败，请稍后重试', 'error')
      } finally {
        isLoading.value = false
      }
    }

    const handleChannelLogin = (channel) => {
      const name = channel === 'qq' ? 'QQ 用户' : '微信用户'
      showToast(`${name}登录成功，正在进入工作台`, 'success')
      setTimeout(() => {
        completeLogin(name)
      }, 400)
    }

    return {
      username,
      password,
      rememberMe,
      showPassword,
      isLoading,
      errors,
      toast,
      handleLogin,
      handleChannelLogin
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(58, 123, 213, 0.08), transparent 24%),
    radial-gradient(circle at bottom right, rgba(94, 114, 228, 0.08), transparent 28%),
    linear-gradient(180deg, #fbfcfe 0%, #f5f7fb 100%);
}

.login-card {
  box-sizing: border-box;
  width: min(440px, 100%);
  padding: 32px;
  border: 1px solid #e8edf5;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 20px 60px rgba(41, 58, 97, 0.08);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  min-width: 0;
}

.logo-box {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, #eef4ff 0%, #f7faff 100%);
  border: 1px solid #e5ecf8;
}

.logo-img {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.card-eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef3ff;
  color: #4567c7;
  font-size: 12px;
  font-weight: 600;
}

.card-header h2 {
  margin: 8px 0 0;
  font-size: 28px;
  color: #172134;
  line-height: 1.2;
}

.login-form {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.field-group {
  display: grid;
  gap: 8px;
}

.field-group span {
  font-size: 14px;
  font-weight: 600;
  color: #344055;
}

.field-group input {
  box-sizing: border-box;
  width: 100%;
  height: 52px;
  padding: 0 16px;
  border: 1px solid #dce4ef;
  border-radius: 16px;
  background: #fff;
  color: #182235;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.field-group input:focus {
  border-color: #7b9cff;
  box-shadow: 0 0 0 4px rgba(123, 156, 255, 0.14);
}

.password-wrap {
  position: relative;
}

.password-wrap input {
  padding-right: 78px;
}

.toggle-btn {
  position: absolute;
  top: 50%;
  right: 14px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: #5570c8;
  font-size: 13px;
  cursor: pointer;
}

.login-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  min-width: 0;
}

.remember-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5e6b84;
}

.helper-text {
  color: #7c879d;
}

.submit-btn {
  height: 52px;
  border: none;
  border-radius: 16px;
  background: #111827;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.95;
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.channel-divider {
  position: relative;
  margin: 22px 0 18px;
  text-align: center;
}

.channel-divider::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e8edf5;
}

.channel-divider span {
  position: relative;
  padding: 0 12px;
  background: #fff;
  color: #8c97ab;
  font-size: 12px;
}

.channel-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  min-width: 0;
}

.channel-btn {
  box-sizing: border-box;
  height: 48px;
  border: 1px solid #dce4ef;
  border-radius: 16px;
  background: #fff;
  color: #344055;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease;
  min-width: 0;
}

.channel-btn:hover {
  background: #f8fbff;
  border-color: #cfd9ea;
}

.channel-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  object-fit: contain;
}

.error-text {
  color: #d84c4c;
  font-size: 12px;
}

.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 10;
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

.toast-enter-active,
.toast-leave-active {
  transition: all 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 640px) {
  .login-page {
    padding: 16px;
  }

  .login-card {
    width: min(100%, 420px);
    padding: 22px 18px;
    border-radius: 22px;
  }

  .card-header {
    gap: 12px;
    margin-bottom: 22px;
  }

  .card-header h2 {
    font-size: 24px;
  }

  .login-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .channel-row {
    grid-template-columns: 1fr;
  }
}
</style>
