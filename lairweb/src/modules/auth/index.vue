<script setup lang="ts">
// 登录 / 注册页：左侧品牌营销面板（AuthHero）+ 右侧表单面板，双栏卡片
// 与后端统一信封契约 { code, message, data }；登录成功写 token + 用户信息，跳转 redirect 或首页
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Eye, EyeOff, CircleAlert, Loader2,
  Mail, Lock, User, MessageCircle,
} from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { authApi, type LoginInput, type RegisterInput } from './api'
import { setToken, setUser, ApiError } from '../../api/request'
import AuthHero from './AuthHero.vue'

const route = useRoute()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const name = ref('')
const email = ref('')
const password = ref('')
const password2 = ref('')
const agreed = ref(false)
const showPw = ref(false)
const showPw2 = ref(false)
const loading = ref(false)
const error = ref('')

// 注册开关：底部「立即注册」只在开放时可点；页面加载与切到注册时实时查询
const allowRegister = ref(false)
const checkingRegister = ref(false)

async function checkRegisterStatus() {
  checkingRegister.value = true
  try {
    const r = await authApi.registerStatus()
    allowRegister.value = r.allowRegister
  } catch {
    allowRegister.value = false
  } finally {
    checkingRegister.value = false
  }
}

checkRegisterStatus()

const isLogin = computed(() => mode.value === 'login')
const title = computed(() => (isLogin.value ? '欢迎回来' : '创建账号'))
const subtitle = computed(() =>
  (isLogin.value ? '登录你的 OpenLair 工作台' : '注册后即可开始使用 OpenLair 工作台'))

function switchMode(m: 'login' | 'register') {
  mode.value = m
  error.value = ''
  // 切到注册时实时复查注册开关；关闭则退回登录并提示
  if (m === 'register') {
    checkRegisterStatus().then(() => {
      if (!allowRegister.value) {
        mode.value = 'login'
        error.value = '系统暂未开放注册，请联系管理员'
      }
    })
  }
}

// 后端暂无自助找回 / 第三方登录流程，点击如实提示，不做死跳转
function onForgot() {
  error.value = '暂未支持自助找回密码，请联系管理员重置'
}
function onOauth(channel: string) {
  error.value = `${channel}登录暂未开放，敬请期待`
}

function validate(): string {
  const mail = email.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return '请输入正确的邮箱地址'
  if (!password.value) return '请输入密码'
  if (isLogin.value) return ''
  if (!name.value.trim()) return '请输入昵称'
  if (password.value.length < 6) return '密码至少 6 位'
  if (password2.value !== password.value) return '两次输入的密码不一致'
  if (!agreed.value) return '请先阅读并同意用户协议和隐私政策'
  return ''
}

async function submit() {
  if (loading.value) return
  if (!isLogin.value && !allowRegister.value) {
    error.value = '系统暂未开放注册，请联系管理员'
    return
  }
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
  <div class="relative grid min-h-dvh place-items-center overflow-hidden bg-background px-4 py-6">
    <!-- 页面右上柔光 -->
    <div class="page-glow" aria-hidden="true"></div>

    <div class="shell relative z-10">
      <!-- 左：品牌营销面板（窄屏隐藏，表单全宽） -->
      <AuthHero class="hidden md:block" />

      <!-- 右：表单面板 -->
      <div class="form-pane bg-card p-6 sm:p-10">
        <div class="mx-auto flex w-full max-w-[400px] flex-col">
          <h1 class="text-2xl font-bold tracking-tight">{{ title }}</h1>
          <p class="mt-1 text-sm text-muted-foreground">{{ subtitle }}</p>

          <form class="mt-6" @submit.prevent="submit">
            <!-- 昵称（仅注册；后端 RegisterInput.name 必填，设计稿未画但不可省） -->
            <template v-if="!isLogin">
              <Label for="auth-name" class="mb-1.5 block text-xs font-medium text-muted-foreground">昵称</Label>
              <div class="relative mb-4">
                <User class="field-icon" />
                <Input
                  id="auth-name"
                  v-model="name"
                  class="h-11 pl-10"
                  type="text"
                  placeholder="你的昵称"
                  maxlength="20"
                  autocomplete="nickname"
                />
              </div>
            </template>

            <!-- 邮箱 -->
            <Label for="auth-email" class="mb-1.5 block text-xs font-medium text-muted-foreground">邮箱</Label>
            <div class="relative mb-4">
              <Mail class="field-icon" />
              <Input
                id="auth-email"
                v-model="email"
                class="h-11 pl-10"
                type="email"
                placeholder="请输入邮箱地址"
                autocomplete="email"
                :autofocus="true"
              />
            </div>

            <!-- 密码 -->
            <Label for="auth-password" class="mb-1.5 block text-xs font-medium text-muted-foreground">密码</Label>
            <div class="relative" :class="isLogin ? '' : 'mb-4'">
              <Lock class="field-icon" />
              <Input
                id="auth-password"
                v-model="password"
                class="h-11 pl-10 pr-11"
                :type="showPw ? 'text' : 'password'"
                placeholder="请输入密码"
                :autocomplete="isLogin ? 'current-password' : 'new-password'"
              />
              <button
                type="button"
                class="eye-btn"
                :title="showPw ? '隐藏密码' : '显示密码'"
                :aria-label="showPw ? '隐藏密码' : '显示密码'"
                @click="showPw = !showPw"
              >
                <EyeOff v-if="showPw" class="size-4" />
                <Eye v-else class="size-4" />
              </button>
            </div>

            <!-- 忘记密码（仅登录） -->
            <div v-if="isLogin" class="mt-2 flex justify-end">
              <button
                type="button"
                class="text-xs font-medium text-[var(--accent)] hover:underline"
                @click="onForgot"
              >忘记密码？</button>
            </div>

            <!-- 确认密码（仅注册） -->
            <template v-if="!isLogin">
              <Label for="auth-password2" class="mb-1.5 mt-4 block text-xs font-medium text-muted-foreground">确认密码</Label>
              <div class="relative">
                <Lock class="field-icon" />
                <Input
                  id="auth-password2"
                  v-model="password2"
                  class="h-11 pl-10 pr-11"
                  :type="showPw2 ? 'text' : 'password'"
                  placeholder="请再次输入密码"
                  autocomplete="new-password"
                />
                <button
                  type="button"
                  class="eye-btn"
                  :title="showPw2 ? '隐藏密码' : '显示密码'"
                  :aria-label="showPw2 ? '隐藏密码' : '显示密码'"
                  @click="showPw2 = !showPw2"
                >
                  <EyeOff v-if="showPw2" class="size-4" />
                  <Eye v-else class="size-4" />
                </button>
              </div>

              <!-- 协议勾选 -->
              <label class="mt-4 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
                <input v-model="agreed" type="checkbox" class="agree-check mt-0.5" />
                <span>我已阅读并同意<span class="agree-link">《用户协议》</span>和<span class="agree-link">《隐私政策》</span></span>
              </label>
            </template>

            <Alert v-if="error" variant="destructive" class="mt-4">
              <CircleAlert class="size-4" />
              <AlertDescription>{{ error }}</AlertDescription>
            </Alert>

            <Button
              type="submit"
              class="cta-btn mt-5 h-12 w-full rounded-[var(--r-pill)] text-[0.98rem] font-bold shadow-[var(--sh-cta)]"
              :disabled="loading"
            >
              <Loader2 v-if="loading" class="size-4 animate-spin" />
              {{ loading ? '请稍候…' : (isLogin ? '登录 →' : '注册') }}
            </Button>
          </form>

          <!-- 其他方式登录（仅登录；后端暂无 OAuth，点击如实提示） -->
          <template v-if="isLogin">
            <div class="my-5 flex items-center gap-3">
              <span class="h-px flex-1 bg-[var(--hairline)]"></span>
              <span class="text-xs text-[var(--text-4)]">其他方式登录</span>
              <span class="h-px flex-1 bg-[var(--hairline)]"></span>
            </div>
            <div class="flex justify-center gap-5">
              <button
                type="button"
                class="oauth-btn"
                title="GitHub 登录"
                aria-label="GitHub 登录"
                @click="onOauth('GitHub')"
              >
                <svg viewBox="0 0 24 24" class="size-5" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.27-.01-1.17-.02-2.12-3.2.7-3.87-1.36-3.87-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.72-1.54-2.55-.29-5.23-1.28-5.23-5.68 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.73.81 1.18 1.83 1.18 3.09 0 4.41-2.69 5.38-5.25 5.66.41.36.77 1.05.77 2.13 0 1.54-.01 2.78-.01 3.16 0 .31.21.68.8.56A11.52 11.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg>
              </button>
              <button
                type="button"
                class="oauth-btn text-[#07c160]"
                title="微信登录"
                aria-label="微信登录"
                @click="onOauth('微信')"
              >
                <MessageCircle class="size-5" />
              </button>
            </div>
          </template>

          <!-- 底部模式切换 -->
          <div class="mt-6 flex items-center justify-center gap-1 text-sm text-muted-foreground">
            <template v-if="isLogin">
              <span>还没有账号？</span>
              <span v-if="checkingRegister" class="text-[var(--text-4)]">检测中…</span>
              <button
                v-else-if="allowRegister"
                type="button"
                class="mode-link"
                @click="switchMode('register')"
              >立即注册</button>
              <span v-else class="text-[var(--text-4)]">注册未开放</span>
            </template>
            <template v-else>
              <span>已有账号？</span>
              <button type="button" class="mode-link" @click="switchMode('login')">立即登录</button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面右上柔光 */
.page-glow {
  position: absolute;
  top: -180px;
  right: -140px;
  width: 480px;
  height: 480px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(10, 132, 255, 0.1), transparent 70%);
  pointer-events: none;
}

/* 双栏卡片：窄屏单栏（左面板隐藏），md 起左营销 + 右表单 */
.shell {
  display: grid;
  grid-template-columns: 1fr;
  width: 100%;
  max-width: 1040px;
  border-radius: var(--r-hero);
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

@media (min-width: 768px) {
  .shell {
    grid-template-columns: 1.08fr 1fr;
    min-height: 640px;
  }
}

.form-pane {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 输入框前缀图标（Input 是裸 input，icon 绝对定位 + pl-10 让位） */
.field-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  width: 16px;
  height: 16px;
  transform: translateY(-50%);
  color: var(--text-3);
  pointer-events: none;
}

/* 密码显隐眼睛 */
.eye-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: var(--text-3);
}

.eye-btn:hover {
  color: var(--text);
  background: var(--hover);
}

/* 协议勾选 */
.agree-check {
  width: 15px;
  height: 15px;
  accent-color: var(--accent);
}

.agree-link {
  color: var(--accent);
}

/* 底部模式切换链接 */
.mode-link {
  color: var(--accent);
  font-weight: 600;
}

.mode-link:hover {
  text-decoration: underline;
}

/* 第三方登录圆钮 */
.oauth-btn {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--hairline);
  color: var(--text);
  background: var(--surface);
  transition: transform 160ms var(--ease-out-quart), box-shadow 160ms var(--ease-out-quart);
}

.oauth-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--sh-card);
}

/* CTA 渐变：--grad-cta 是 background-image，必须走 background 简写，写 background-color 会失效变透明 */
.cta-btn {
  background: var(--grad-cta);
  color: #fff;
}

.cta-btn:hover {
  background: var(--grad-cta);
}
</style>
