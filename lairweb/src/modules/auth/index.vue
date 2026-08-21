<script setup lang="ts">
// 登录 / 注册页：与后端统一信封契约 { code, message, data }
// 登录成功后写入 token + 用户信息到 localStorage，跳转 redirect 或首页
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, CircleAlert, Loader2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
  <div class="relative grid min-h-dvh place-items-center overflow-hidden bg-background px-4 py-6">
    <!-- 氛围光斑（克制：仅背景，不参与内容层级） -->
    <div class="glow glow-a" aria-hidden="true"></div>
    <div class="glow glow-b" aria-hidden="true"></div>

    <div class="relative z-10 w-full max-w-[400px] rounded-[var(--r-hero)] bg-card p-6 shadow-[var(--sh-panel)] sm:p-8">
      <div class="mb-6 flex flex-col items-center gap-1.5">
        <span class="brand-mark">L</span>
        <h1 class="mt-2 text-2xl font-bold tracking-tight">OpenLair</h1>
        <p class="text-[13px] text-muted-foreground">个人 AI 生活工作台</p>
      </div>

      <div class="seg mb-6 grid grid-cols-2 gap-1 p-1" role="tablist">
        <button class="seg-btn" :class="{ on: isLogin }" @click="switchMode('login')">登录</button>
        <button class="seg-btn" :class="{ on: !isLogin }" @click="switchMode('register')">注册</button>
      </div>

      <h2 class="text-2xl font-bold tracking-tight">{{ title }}</h2>
      <p class="mt-1 text-sm text-muted-foreground">{{ subtitle }}</p>

      <form class="mt-4" @submit.prevent="submit">
        <template v-if="!isLogin">
          <Label for="auth-name" class="mb-1.5 mt-4 block text-xs font-medium text-muted-foreground">昵称</Label>
          <Input
            id="auth-name"
            v-model="name"
            class="h-11"
            type="text"
            placeholder="你的昵称"
            maxlength="20"
            autocomplete="nickname"
          />
        </template>

        <Label for="auth-email" class="mb-1.5 mt-4 block text-xs font-medium text-muted-foreground">邮箱</Label>
        <Input
          id="auth-email"
          v-model="email"
          class="h-11"
          type="email"
          placeholder="you@example.com"
          autocomplete="email"
          :autofocus="true"
        />

        <Label for="auth-password" class="mb-1.5 mt-4 block text-xs font-medium text-muted-foreground">密码</Label>
        <div class="relative">
          <Input
            id="auth-password"
            v-model="password"
            class="h-11 pr-12"
            :type="showPw ? 'text' : 'password'"
            :placeholder="isLogin ? '输入密码' : '至少 6 位'"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="absolute right-1 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            :title="showPw ? '隐藏密码' : '显示密码'"
            :aria-label="showPw ? '隐藏密码' : '显示密码'"
            @click="showPw = !showPw"
          >
            <EyeOff v-if="showPw" class="size-4" />
            <Eye v-else class="size-4" />
          </Button>
        </div>

        <Alert v-if="error" variant="destructive" class="mt-4">
          <CircleAlert class="size-4" />
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>

        <Button type="submit" class="cta mt-5 w-full" :disabled="loading">
          <Loader2 v-if="loading" class="size-4 animate-spin" />
          {{ loading ? '请稍候…' : isLogin ? '登录' : '注册并登录' }}
        </Button>
      </form>

      <p v-if="isLogin" class="demo-hint">测试账号：test1@openlair.dev / test2@openlair.dev / test3@openlair.dev<br />密码统一 test123456</p>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════════════
   auth page — shadcn 组件 + Apple Liquid Glass token
   仅保留无法用 Tailwind utility 表达的部分（光斑 / 品牌标记 / 分段控件 / CTA 渐变）
   ════════════════════════════════════════════════════════════ */

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

/* 品牌标记（渐变 + CTA 玻璃阴影） */
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

/* 分段控件（白胶囊 segmented，components.md §5） */
.seg {
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

/* 主 CTA：覆盖 Button 默认纯色背景，改用渐变 + 玻璃阴影 */
.cta {
  height: 48px;
  border-radius: var(--r-pill);
  background: var(--grad-cta);
  font-size: 0.98rem;
  font-weight: 700;
  box-shadow: var(--sh-cta);
}
.cta:hover {
  background: var(--grad-cta);
  box-shadow: 0 22px 60px rgba(0, 113, 227, 0.3);
}

/* 演示账号提示 */
.demo-hint {
  margin: 18px 0 0;
  text-align: center;
  color: var(--text-4);
  font-size: 0.76rem;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .brand-mark {
    width: 50px;
    height: 50px;
    border-radius: 16px;
  }
}
</style>
