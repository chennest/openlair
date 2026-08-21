<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUser } from '../../api/request'
import { authApi, type AuthUser } from '../auth/api'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'

// ---------- 三态：loading / error / data（规范 §3.3） ----------
const loading = ref(true)
const error = ref('')
const profile = ref<AuthUser | null>(null)

onMounted(async () => {
  try {
    profile.value = await authApi.me()
  } catch {
    // API 失败时回退到本地缓存的用户数据
    const local = getUser() as AuthUser | null
    if (local) {
      profile.value = local
    } else {
      error.value = '加载个人信息失败，请重新登录'
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="mx-auto w-full max-w-[var(--max-read)]">
    <!-- loading -->
    <div v-if="loading" class="grid min-h-[40vh] place-items-center">
      <div class="flex w-full flex-col items-center gap-3">
        <Skeleton class="size-20 rounded-full" />
        <Skeleton class="h-4 w-40" />
        <Skeleton class="h-4 w-56" />
      </div>
    </div>

    <!-- error -->
    <div v-else-if="error" class="grid min-h-[40vh] place-items-center">
      <p class="text-sm text-destructive">{{ error }}</p>
    </div>

    <!-- data -->
    <template v-else-if="profile">
      <h1 class="page-title">个人信息</h1>

      <div class="rounded-[var(--r-panel)] bg-card p-6 shadow-[var(--sh-panel)] sm:p-9">
        <!-- 大号圆形头像 -->
        <div class="mb-7 flex justify-center">
          <Avatar class="size-20">
            <AvatarFallback class="text-3xl font-bold text-white" :style="{ background: profile.avatarColor }">
              {{ profile.name.slice(0, 1) }}
            </AvatarFallback>
          </Avatar>
        </div>

        <!-- 信息行（hairline 分割，最后一行无下边框） -->
        <div class="divide-y divide-border">
          <div class="flex items-center justify-between px-2 py-3.5">
            <span class="text-[15px] font-medium text-muted-foreground">昵称</span>
            <span class="text-[15px] font-semibold">{{ profile.name }}</span>
          </div>

          <div class="flex items-center justify-between px-2 py-3.5">
            <span class="text-[15px] font-medium text-muted-foreground">邮箱</span>
            <span class="text-[15px] font-semibold">{{ profile.email }}</span>
          </div>

          <div class="flex items-center justify-between px-2 py-3.5">
            <span class="text-[15px] font-medium text-muted-foreground">注册时间</span>
            <span class="text-[15px] font-semibold tabular-nums">{{
              new Date(profile.createdAt).toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })
            }}</span>
          </div>

          <div class="flex items-center justify-between px-2 py-3.5">
            <span class="text-[15px] font-medium text-muted-foreground">用户 ID</span>
            <span class="font-mono text-[13px] font-medium tabular-nums">{{ profile.id }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ---------- 大标题（H1 规范：负字距 700） ---------- */
.page-title {
  margin: 0 0 clamp(28px, 5vw, 40px);
  font-size: clamp(27px, 5vw, 46px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
}
</style>
