<script setup lang="ts">
import { computed, ref } from 'vue'

type AssistantResponse = {
  message: string
  session_id: string
  route: string
}

type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  meta?: string
}

const prompt = ref('帮我总结一下今天应该优先推进什么。')
const sessionId = ref('web-local')
const userId = ref('local-user')
const isSending = ref(false)
const errorMessage = ref('')
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
const messages = ref<ChatMessage[]>([
  {
    id: 1,
    role: 'assistant',
    content: 'OpenLair Web 已接入后端助手入口。启动 lairservice 后，可以在这里直接调用 /assistant/invoke。',
    meta: 'system · ready',
  },
])

const canSend = computed(() => prompt.value.trim().length > 0 && !isSending.value)

async function invokeAssistant() {
  const message = prompt.value.trim()
  if (!message) return

  errorMessage.value = ''
  isSending.value = true
  messages.value.push({ id: Date.now(), role: 'user', content: message, meta: sessionId.value })
  prompt.value = ''

  try {
    const response = await fetch(`${apiBaseUrl}/assistant/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        user_id: userId.value || 'local-user',
        session_id: sessionId.value || 'web-local',
      }),
    })

    if (!response.ok) {
      throw new Error(`Assistant request failed with ${response.status}`)
    }

    const data = (await response.json()) as AssistantResponse
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: data.message,
      meta: `${data.route} · ${data.session_id}`,
    })
    sessionId.value = data.session_id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Assistant request failed'
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <main class="shell">
    <section class="hero-panel" aria-labelledby="page-title">
      <div class="brand-row">
        <span class="brand-mark">穴</span>
        <span class="brand-name">OpenLair Web</span>
      </div>
      <p class="eyebrow">Vue 3 · TypeScript · FastAPI</p>
      <h1 id="page-title">一个可直接连接真实模型的控制台。</h1>
      <p class="lede">
        后端 agent harness 已经跑通真实模型测试；这个 Web 入口先聚焦最重要的闭环：把用户输入送进
        <code>/assistant/invoke</code>，把 LangGraph runtime 的回答带回来。
      </p>

      <div class="status-grid" aria-label="Runtime status">
        <div>
          <span>Backend</span>
          <strong>FastAPI</strong>
        </div>
        <div>
          <span>Model route</span>
          <strong>agent</strong>
        </div>
        <div>
          <span>Session</span>
          <strong>{{ sessionId || 'web-local' }}</strong>
        </div>
      </div>
    </section>

    <section class="console-card" aria-labelledby="console-title">
      <div class="console-header">
        <div>
          <p class="eyebrow">Assistant Console</p>
          <h2 id="console-title">本地助手会话</h2>
        </div>
        <div class="live-pill"><span></span> {{ apiBaseUrl || 'Vite proxy' }}</div>
      </div>

      <div class="messages" aria-live="polite">
        <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
          <div class="message-meta">{{ message.role }} · {{ message.meta }}</div>
          <p>{{ message.content }}</p>
        </article>
      </div>

      <form class="composer" @submit.prevent="invokeAssistant">
        <div class="identity-row">
          <label>
            User
            <input v-model="userId" autocomplete="off" />
          </label>
          <label>
            Session
            <input v-model="sessionId" autocomplete="off" />
          </label>
        </div>
        <label class="prompt-label" for="prompt">Message</label>
        <textarea
          id="prompt"
          v-model="prompt"
          :disabled="isSending"
          rows="4"
          placeholder="输入要交给 OpenLair agent 的任务…"
        />
        <div class="composer-footer">
          <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
          <p v-else>本地代理目标来自 <code>LAIRWEB_API_PROXY_TARGET</code>；浏览器默认使用同源 Vite proxy。</p>
          <button type="submit" :disabled="!canSend">
            {{ isSending ? '发送中…' : '发送给助手' }}
          </button>
        </div>
      </form>
    </section>
  </main>
</template>
