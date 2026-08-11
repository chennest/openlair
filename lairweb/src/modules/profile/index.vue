<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUser } from '../../api/request'
import { authApi, type AuthUser } from '../auth/api'

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
  <div class="profile-page">
    <!-- loading -->
    <div v-if="loading" class="state-box">
      <p class="state-text">加载中…</p>
    </div>

    <!-- error -->
    <div v-else-if="error" class="state-box">
      <p class="state-text is-error">{{ error }}</p>
    </div>

    <!-- data -->
    <template v-else-if="profile">
      <h1 class="page-title">个人信息</h1>

      <div class="panel">
        <!-- 大号圆形头像 -->
        <div class="avatar-row">
          <div
            class="avatar-circle"
            :style="{ background: profile.avatarColor }"
          >
            {{ profile.name.slice(0, 1) }}
          </div>
        </div>

        <!-- 昵称 -->
        <div class="info-row">
          <span class="label">昵称</span>
          <span class="value">{{ profile.name }}</span>
        </div>

        <!-- 邮箱 -->
        <div class="info-row">
          <span class="label">邮箱</span>
          <span class="value">{{ profile.email }}</span>
        </div>

        <!-- 注册时间 -->
        <div class="info-row">
          <span class="label">注册时间</span>
          <span class="value value-num">{{
            new Date(profile.createdAt).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })
          }}</span>
        </div>

        <!-- 用户 ID -->
        <div class="info-row is-last">
          <span class="label">用户 ID</span>
          <span class="value value-mono">{{ profile.id }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ---------- 页面容器（reading width） ---------- */
.profile-page {
  max-width: var(--max-read);
  margin: 0 auto;
}

/* ---------- 大标题（H1 规范：负字距 700） ---------- */
.page-title {
  margin: 0 0 clamp(28px, 5vw, 40px);
  font-size: clamp(27px, 5vw, 46px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
}

/* ---------- 统一面板（surface + panel 阴影 + panel 圆角） ---------- */
.panel {
  padding: clamp(24px, 5vw, 36px);
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}

/* ---------- 头像 ---------- */
.avatar-row {
  display: flex;
  justify-content: center;
  margin-bottom: 28px;
}

.avatar-circle {
  width: 80px;
  height: 80px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  font-size: 2rem;
  font-weight: 700;
}

/* ---------- 信息行（hairline 分割线，最后一行无边框） ---------- */
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 8px;
  border-bottom: 1px solid var(--hairline);
}

.info-row.is-last {
  border-bottom: 0;
}

.label {
  color: var(--text-2);
  font-size: 0.92rem;
  font-weight: 500;
}

.value {
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 600;
}

/* 数字用 tabular-nums */
.value-num {
  font-variant-numeric: tabular-nums;
}

/* 用户 ID 用等宽字体 */
.value-mono {
  font-family: var(--mono);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}

/* ---------- 状态占位 ---------- */
.state-box {
  display: grid;
  place-items: center;
  min-height: 40vh;
}

.state-text {
  color: var(--text-3);
  font-size: 0.94rem;
}

.state-text.is-error {
  color: var(--heat);
}
</style>
