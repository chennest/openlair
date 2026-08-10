<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  assistantApi,
  streamChat,
  type AssistantSession,
  type AssistantMessage,
  type ChatEvent,
} from './api'

// ---------- UI 消息（扩展后端消息 + 前端流式/确认状态） ----------
interface UIMessage {
  id: number | string
  role: 'user' | 'assistant'
  content: string
  meta?: Record<string, unknown>
  createdAt?: string
  /** 正在流式接收 */
  streaming?: boolean
  /** 待确认计划 */
  pendingPlan?: { planId: string; summary: string }
}

// ---------- 状态 ----------
const sessions = ref<AssistantSession[]>([])
const currentSessionId = ref<number | null>(null)
const messages = ref<UIMessage[]>([])
const inputText = ref('')
const loading = ref(true)
const sending = ref(false)
const confirming = ref<string | null>(null) // 正在确认的 planId
const error = ref('')
const msgContainer = ref<HTMLElement | null>(null)
const aborter = ref<AbortController | null>(null)

// 是否为空态（无会话或无消息）
const isWelcome = computed(() => !currentSessionId.value || messages.value.length === 0)

// ---------- 生命周期 ----------
onMounted(async () => {
  await loadSessions()
})

onBeforeUnmount(() => {
  aborter.value?.abort()
})

// ---------- 会话 ----------
async function loadSessions() {
  loading.value = true
  error.value = ''
  try {
    sessions.value = await assistantApi.sessions()
    // 如果有历史会话，默认选最近一个；否则进入欢迎态
    if (sessions.value.length > 0 && !currentSessionId.value) {
      currentSessionId.value = sessions.value[0].id
      await loadMessages()
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载会话失败'
  } finally {
    loading.value = false
  }
}

async function selectSession(id: number) {
  if (id === currentSessionId.value) return
  currentSessionId.value = id
  messages.value = []
  await loadMessages()
  scrollToBottom()
}

async function createSession() {
  try {
    const s = await assistantApi.createSession()
    sessions.value.unshift(s)
    currentSessionId.value = s.id
    messages.value = []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建会话失败'
  }
}

async function loadMessages() {
  if (!currentSessionId.value) return
  try {
    const msgs = await assistantApi.messages(currentSessionId.value)
    messages.value = msgs.map((m: AssistantMessage) => ({ ...m }))
    await nextTick(() => scrollToBottom())
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载消息失败'
  }
}

// ---------- 发送消息 + SSE 流式接收 ----------
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value) return

  // 确保有会话
  if (!currentSessionId.value) {
    try {
      const s = await assistantApi.createSession()
      sessions.value.unshift(s)
      currentSessionId.value = s.id
    } catch (e) {
      error.value = e instanceof Error ? e.message : '创建会话失败'
      return
    }
  }

  inputText.value = ''
  sending.value = true
  error.value = ''

  // 追加用户消息
  const userMsg: UIMessage = { id: `user-${Date.now()}`, role: 'user', content: text }
  messages.value.push(userMsg)

  // 创建 assistant 占位消息
  const aiMsg: UIMessage = {
    id: `ai-${Date.now()}`,
    role: 'assistant',
    content: '',
    streaming: true,
  }
  messages.value.push(aiMsg)
  await nextTick(() => scrollToBottom())

  const controller = new AbortController()
  aborter.value = controller

  // 记录本轮是否在 streaming
  let streamDone = false

  void streamChat(
    currentSessionId.value,
    text,
    // onEvent
    (evt: ChatEvent) => {
      switch (evt.type) {
        case 'message_delta':
          aiMsg.content += evt.delta
          break
        case 'confirm_request':
          aiMsg.streaming = false
          // 追加请求确认的卡片信息
          aiMsg.pendingPlan = { planId: evt.planId, summary: evt.summary }
          break
        case 'done':
          streamDone = true
          aiMsg.streaming = false
          refreshSessionsSilent()
          break
        case 'error':
          aiMsg.content += aiMsg.content ? `\n\n⚠️ ${evt.message}` : `⚠️ ${evt.message}`
          aiMsg.streaming = false
          streamDone = true
          break
      }
      void nextTick(() => scrollToBottom())
    },
    // onError
    (msg: string) => {
      aiMsg.content = `⚠️ ${msg}`
      aiMsg.streaming = false
      streamDone = true
    },
    controller.signal,
  ).finally(() => {
    sending.value = false
    // 如果没收到 done 且没错误 → 流异常中断
    if (!streamDone && aiMsg.content === '') {
      aiMsg.content = '（响应中断）'
    }
    aiMsg.streaming = false
    aborter.value = null
  })
}

// ---------- 确认卡片 ----------
async function handleConfirm(planId: string, approved: boolean) {
  confirming.value = planId
  try {
    const result = await assistantApi.confirm(planId, approved)
    // 把确认结果作为新的 assistant 消息追加
    messages.value.push({ id: `confirm-${Date.now()}`, role: 'assistant', content: result.message })
    await nextTick(() => scrollToBottom())
    refreshSessionsSilent()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    confirming.value = null
  }
}

/** 静默刷新会话列表（更新标题/时间，不显示 loading） */
async function refreshSessionsSilent() {
  try {
    sessions.value = await assistantApi.sessions()
  } catch {
    // 静默失败
  }
}

// ---------- 工具方法 ----------
function scrollToBottom() {
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void sendMessage()
  }
}

// 示例问题点击
function onExample(text: string) {
  inputText.value = text
  void sendMessage()
}

// ---------- 会话标题裁剪 ----------
function sessionLabel(s: AssistantSession): string {
  return s.title.length > 12 ? s.title.slice(0, 12) + '…' : s.title
}

// ---------- watch 会话变化 → 刷新会话列表（标题实时更新） ----------
watch(currentSessionId, () => {
  void refreshSessionsSilent()
})
</script>

<template>
  <div class="assistant-page">
    <!-- 会话 Chip 行 -->
    <div class="session-bar">
      <div class="session-chips">
        <button class="chip is-new" @click="createSession" title="新建会话">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               class="chip-icon">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>新对话</span>
        </button>
        <button
          v-for="s in sessions"
          :key="s.id"
          class="chip"
          :class="{ 'is-active': s.id === currentSessionId }"
          @click="selectSession(s.id)"
        >
          {{ sessionLabel(s) }}
        </button>
      </div>
    </div>

    <!-- 消息区 -->
    <div ref="msgContainer" class="msg-area">
      <div v-if="loading" class="placeholder"><div><p>正在加载…</p></div></div>

      <div v-else-if="error && !currentSessionId" class="placeholder">
        <div><p class="symbol">!</p><p>{{ error }}</p></div>
      </div>

      <!-- 欢迎态 -->
      <div v-else-if="isWelcome" class="welcome">
        <div class="welcome-inner">
          <h1 class="welcome-title">AI 助手</h1>
          <p class="welcome-sub">
            用一句话记账，让 AI 帮你识别分类与金额
          </p>
          <div class="welcome-examples">
            <button
              v-for="q in ['记一笔：午饭 68 元', '昨天打车花了 30', '收到工资 8000']"
              :key="q"
              class="example-btn"
              @click="onExample(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <template v-else>
        <TransitionGroup name="msg" tag="div" class="msg-list">
          <div
            v-for="m in messages"
            :key="m.id"
            class="msg-row"
            :class="m.role"
          >
            <!-- 用户消息：右对齐蓝色气泡 -->
            <div v-if="m.role === 'user'" class="msg-bubble user">
              {{ m.content }}
            </div>

            <!-- AI 消息：左对齐白色面板 -->
            <div v-else class="msg-bubble assistant">
              <span v-if="m.content" class="msg-text">{{ m.content }}</span>
              <span
                v-if="m.streaming"
                class="stream-cursor"
                aria-label="AI 正在输入"
              >|</span>

              <!-- 确认卡片 -->
              <div
                v-if="m.pendingPlan"
                class="confirm-card"
              >
                <div class="confirm-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                       class="confirm-icon">
                    <path d="M9 12l2 2 4-4" />
                    <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-2a2 2 0 0 1 0-4 10 10 0 0 0 0-14h0z" />
                  </svg>
                  <span>确认记账</span>
                </div>
                <p class="confirm-summary">{{ m.pendingPlan.summary }}</p>
                <div class="confirm-actions">
                  <button
                    class="confirm-btn is-outline"
                    :disabled="confirming === m.pendingPlan.planId"
                    @click="handleConfirm(m.pendingPlan!.planId, false)"
                  >
                    {{ confirming === m.pendingPlan.planId ? '…' : '取消' }}
                  </button>
                  <button
                    class="confirm-btn is-accent"
                    :disabled="confirming === m.pendingPlan.planId"
                    @click="handleConfirm(m.pendingPlan!.planId, true)"
                  >
                    {{ confirming === m.pendingPlan.planId ? '处理中…' : '确认' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </TransitionGroup>

        <!-- 流式发送中提示（无 assistant 消息时） -->
        <div v-if="sending && messages.length === 0" class="placeholder">
          <div><p>AI 正在思考…</p></div>
        </div>
      </template>
    </div>

    <!-- 底部输入区 -->
    <div class="input-bar">
      <div class="input-row">
        <textarea
          v-model="inputText"
          class="input-field"
          placeholder="用一句话记账，比如：昨天午饭花了 68"
          :disabled="sending"
          rows="1"
          @keydown="onKeydown"
        ></textarea>
        <button
          class="send-btn"
          :disabled="!inputText.trim() || sending"
          @click="sendMessage"
          aria-label="发送消息"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"
               class="send-icon">
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══ 页面容器 ═══ */
.assistant-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  height: calc(100dvh - 64px);
  max-width: var(--max-read);
  margin: 0 auto;
}

/* ═══ 会话 Chip 行 ═══ */
.session-bar {
  flex: 0 0 auto;
  padding: 16px 0 8px;
}

.session-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  padding: 0 var(--pad-x);
}

.session-chips::-webkit-scrollbar { display: none; }

.chip {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  background: var(--surface);
  color: var(--text-2);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease, border-color 160ms ease;
  white-space: nowrap;
}

.chip:hover {
  color: var(--text);
  background: var(--hover);
}

.chip.is-active {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.24);
}

.chip.is-new {
  color: var(--accent);
}

.chip-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
}

/* ═══ 消息区域 ═══ */
.msg-area {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--pad-x) 16px;
}

.msg-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ═══ 欢迎态 ═══ */
.welcome {
  display: grid;
  place-items: center;
  min-height: 60%;
  text-align: center;
  padding: 20px 0;
}

.welcome-inner {
  max-width: 400px;
}

.welcome-title {
  margin: 0 0 10px;
  font-size: clamp(1.6rem, 3vw, 2.2rem);
  letter-spacing: -0.03em;
  line-height: 1.12;
  color: var(--text);
}

.welcome-sub {
  margin: 0 0 28px;
  color: var(--text-2);
  font-size: 0.94rem;
  line-height: 1.6;
}

.welcome-examples {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.example-btn {
  display: block;
  width: 100%;
  padding: 13px 18px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-card);
  background: var(--surface);
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  box-shadow: var(--sh-card);
  transition: box-shadow 200ms var(--ease-out-quart), border-color 200ms ease;
}

.example-btn:hover {
  border-color: var(--accent);
  box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 6px 18px rgba(0,0,0,0.06);
}

/* ═══ 消息气泡 ═══ */
.msg-row {
  display: flex;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.assistant {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 82%;
  line-height: 1.58;
}

/* 用户气泡：蓝底白字，右对齐 */
.msg-bubble.user {
  padding: 11px 17px;
  border-radius: var(--r-card);
  background: var(--accent);
  color: #fff;
  font-size: 0.92rem;
  font-weight: 500;
}

/* AI 气泡：白底灰字，左对齐，柔和阴影 */
.msg-bubble.assistant {
  padding: 14px 18px;
  border-radius: var(--r-card);
  background: var(--surface);
  border: 1px solid var(--hairline);
  box-shadow: var(--sh-card);
  font-size: 0.92rem;
  color: var(--text-body);
}

.msg-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 流式光标 */
.stream-cursor {
  animation: blink 800ms steps(1, end) infinite;
  color: var(--accent);
  font-weight: 300;
  margin-left: 1px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ═══ 确认卡片 ═══ */
.confirm-card {
  margin-top: 14px;
  padding: 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  background: var(--surface);
  box-shadow: var(--sh-card);
}

.confirm-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}

.confirm-icon {
  width: 20px;
  height: 20px;
  color: var(--accent);
}

.confirm-summary {
  margin: 0 0 16px;
  color: var(--text-2);
  font-size: 0.85rem;
  line-height: 1.55;
}

.confirm-actions {
  display: flex;
  gap: 10px;
}

.confirm-btn {
  flex: 1;
  min-height: 44px;
  padding: 10px 16px;
  border-radius: var(--r-pill);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 160ms ease;
}

.confirm-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.confirm-btn.is-accent {
  background: var(--accent);
  color: #fff;
}

.confirm-btn.is-outline {
  background: transparent;
  color: var(--text-2);
  border-color: var(--hairline);
}

.confirm-btn.is-outline:hover:not(:disabled) {
  color: var(--text);
  border-color: rgba(0,0,0,0.18);
}

/* ═══ 底部输入区 ═══ */
.input-bar {
  flex: 0 0 auto;
  padding: 12px var(--pad-x) calc(12px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--hairline);
  background: var(--bg);
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 8px 8px 18px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-pill);
  background: var(--surface);
  box-shadow: var(--sh-card);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.input-row:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.18);
}

.input-field {
  flex: 1;
  min-height: 24px;
  max-height: 120px;
  padding: 3px 0;
  border: 0;
  background: transparent;
  color: var(--text);
  font-size: 0.92rem;
  line-height: 1.55;
  resize: none;
  outline: none;
  font-family: inherit;
}

.input-field::placeholder {
  color: var(--text-4);
}

.input-field:disabled {
  opacity: 0.5;
}

.send-btn {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  transition: opacity 160ms ease, transform 100ms ease;
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.send-icon {
  width: 18px;
  height: 18px;
}

/* ═══ 消息入场动效（轻量淡入） ═══ */
.msg-enter-active {
  transition: opacity 280ms var(--ease-out-quart), transform 280ms var(--ease-out-quart);
}

.msg-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

/* ═══ 响应式 ═══ */
@media (max-width: 860px) {
  .assistant-page {
    height: 100%;
    max-width: none;
  }

  .msg-area {
    padding: 0 0 16px;
  }

  .input-bar {
    padding: 10px 0 calc(10px + env(safe-area-inset-bottom, 0px));
  }

  .msg-bubble {
    max-width: 90%;
  }
}

/* ═══ 减少动效 / 透明度 / 对比度 ═══ */
@media (prefers-reduced-motion: reduce) {
  .stream-cursor { animation: none; }
  .msg-enter-active { transition: opacity 150ms ease; }
  .msg-enter-from { transform: none; }
}

@media (prefers-reduced-transparency: reduce) {
  .session-bar { background: var(--surface); }
}

@media (prefers-contrast: more) {
  .input-row { border-color: rgba(0,0,0,0.35); }
  .confirm-card { border-color: rgba(0,0,0,0.25); }
}
</style>
