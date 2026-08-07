<script setup lang="ts">
// 登录 / 注册页：与后端统一信封契约 { code, message, data }
// 登录成功后写入 token + 用户信息到 localStorage，跳转 redirect 或首页
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi, type LoginInput, type RegisterInput } from './api'
import { setToken, setUser, ApiError } from '../../api/request'

const route = useRoute()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const name = ref('')
const email = ref('')
const password = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')

const isLogin = computed(() => mode.value === 'login')
const title = computed(() => (isLogin.value ? '欢迎回来' : '创建账号'))
const subtitle = computed(() => (isLogin.value ? '登录你的 OpenLair 工作台' : '注册后即可开始记账与日程管理'))

const iconProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': 1.75,
  'stroke-linecap': 'round' as const,
  'stroke-linejoin': 'round' as const,
}

function switchMode(m: 'login' | 'register') {
  mode.value = m
  error.value = ''
}

function validate(): string {
  const mail = email.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return '请输入正确的邮箱地址'
  if (!password.value) return '请输入密码'
  if (isLogin.value) return ''
  if (!name.value.trim()) return '请输入昵称'
  if (password.value.length < 6) return '密码至少 6 位'
  return ''
}

async function submit() {
  if (loading.value) return
  const invalid = validate()
  if (invalid) {
    error.value = invalid
    return
  }
  loading.value = true
  error.value = ''
  try {
    const result = isLogin.value
      ? await authApi.login({ email: email.value.trim(), password: password.value } satisfies LoginInput)
      : await authApi.register({ name: name.value.trim(), email: email.value.trim(), password: password.value } satisfies RegisterInput)
    setToken(result.token)
    setUser(result.user)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect ? route.query.redirect : '/'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <!-- 氛围光斑（克制：仅背景，不参与内容层级） -->
    <div class="glow glow-a" aria-hidden="true"></div>
    <div class="glow glow-b" aria-hidden="true"></div>

    <div class="auth-card">
      <div class="brand">
        <span class="brand-mark">穴</span>
        <h1>OpenLair</h1>
        <p>个人 AI 生活工作台</p>
      </div>

      <div class="seg" role="tablist">
        <button class="seg-btn" :class="{ on: isLogin }" @click="switchMode('login')">登录</button>
        <button class="seg-btn" :class="{ on: !isLogin }" @click="switchMode('register')">注册</button>
      </div>

      <h2 class="page-title">{{ title }}</h2>
      <p class="page-sub">{{ subtitle }}</p>

      <form class="form" @submit.prevent="submit">
        <template v-if="!isLogin">
          <label class="field-label" for="auth-name">昵称</label>
          <input
            id="auth-name"
            v-model="name"
            class="input"
            type="text"
            placeholder="你的昵称"
            maxlength="20"
            autocomplete="nickname"
          />
        </template>

        <label class="field-label" for="auth-email">邮箱</label>
        <input
          id="auth-email"
          v-model="email"
          class="input"
          type="email"
          placeholder="you@example.com"
          autocomplete="email"
          :autofocus="true"
        />

        <label class="field-label" for="auth-password">密码</label>
        <div class="pw-box">
          <input
            id="auth-password"
            v-model="password"
            class="input pw-input"
            :type="showPw ? 'text' : 'password'"
            :placeholder="isLogin ? '输入密码' : '至少 6 位'"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
          />
          <button
            type="button"
            class="pw-toggle"
            :title="showPw ? '隐藏密码' : '显示密码'"
            :aria-label="showPw ? '隐藏密码' : '显示密码'"
            @click="showPw = !showPw"
          >
            <svg v-if="showPw" v-bind="iconProps" aria-hidden="true">
              <path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49" />
              <path d="M14.084 14.158a3 3 0 0 1-4.242-4.242" />
              <path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143" />
              <path d="m2 2 20 20" />
            </svg>
            <svg v-else v-bind="iconProps" aria-hidden="true">
              <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
              <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0" />
            </svg>
          </button>
        </div>

        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <button class="cta" type="submit" :disabled="loading">
          {{ loading ? '请稍候…' : isLogin ? '登录' : '注册并登录' }}
        </button>
      </form>

      <p v-if="isLogin" class="demo-hint">测试账号：me@openlair.dev / openlair123</p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 24px 18px;
  overflow: hidden;
  background: var(--bg);
}

/* 氛围光斑：非常淡的蓝紫渐变，克制 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.glow-a {
  width: 420px;
  height: 420px;
  top: -140px;
  left: -100px;
  background: rgba(10, 132, 255, 0.16);
}
.glow-b {
  width: 380px;
  height: 380px;
  bottom: -120px;
  right: -80px;
  background: rgba(94, 92, 230, 0.14);
}

.auth-card {
  position: relative;
  z-index: 1;
  width: min(400px, 100%);
  padding: 34px 32px 28px;
  border-radius: var(--r-hero);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 26px;
}
.brand-mark {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  color: #fff;
  background: var(--grad-blue);
  font-weight: 800;
  font-size: 1.35rem;
  box-shadow: var(--sh-cta);
}
.brand h1 {
  margin: 8px 0 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.brand p {
  margin: 0;
  color: var(--text-3);
  font-size: 0.82rem;
}

/* 分段控件（白胶囊 segmented，components.md §5） */
.seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: var(--r-pill);
  background: rgba(0, 0, 0, 0.05);
}
.seg-btn {
  padding: 10px;
  border: 0;
  border-radius: var(--r-pill);
  color: var(--text-2);
  background: transparent;
  font-weight: 600;
  cursor: pointer;
  transition: all 160ms var(--ease-out-quart);
}
.seg-btn.on {
  color: var(--text);
  background: var(--surface);
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.page-title {
  margin: 24px 0 4px;
  font-size: 1.45rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.page-sub {
  margin: 0 0 6px;
  color: var(--text-3);
  font-size: 0.84rem;
}

.field-label {
  display: block;
  margin: 16px 0 7px;
  color: var(--text-3);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  outline: none;
  color: var(--text);
  background: var(--surface);
  font: inherit;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}
.input::placeholder {
  color: var(--text-4);
}

.pw-box {
  position: relative;
}
.pw-input {
  padding-right: 48px;
}
.pw-toggle {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--r-thumb);
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease;
}
.pw-toggle:hover {
  color: var(--text);
  background: var(--hover);
}
.pw-toggle svg {
  width: 20px;
  height: 20px;
}

.error {
  margin: 14px 0 0;
  color: var(--heat);
  font-size: 0.82rem;
  font-weight: 600;
}

.cta {
  width: 100%;
  height: 48px;
  margin-top: 22px;
  border: 0;
  border-radius: var(--r-pill);
  color: #fff;
  background: var(--grad-cta);
  font-size: 0.98rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--sh-cta);
  transition: transform 160ms var(--ease-out-quart), box-shadow 160ms var(--ease-out-quart), opacity 160ms ease;
}
.cta:hover {
  box-shadow: 0 22px 60px rgba(0, 113, 227, 0.3);
}
.cta:active {
  transform: scale(0.97);
}
.cta:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.demo-hint {
  margin: 18px 0 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.76rem;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .auth-card {
    padding: 28px 22px 22px;
    border-radius: var(--r-panel);
  }
  .brand-mark {
    width: 50px;
    height: 50px;
    border-radius: 16px;
  }
}
</style>
