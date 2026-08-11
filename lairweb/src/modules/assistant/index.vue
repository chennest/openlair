<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  assistantApi,
  streamChat,
  type AssistantSession,
  type ChatEvent,
} from './api'
import { ApiError, getToken } from '../../api/request'

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
  /** 确认卡片执行结果（确认/取消后原地替换按钮，不再追加重复消息） */
  confirmResult?: { state: 'executed' | 'cancelled' | 'failed'; message: string }
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
const drawerOpen = ref(false)
const inputEl = ref<HTMLElement | null>(null)
const delConfirmId = ref<number | null>(null)

// ---------- 语音输入状态 ----------
const isRecording = ref(false)
const transcribing = ref(false)
const mediaRecorder = ref<MediaRecorder | null>(null)
const mediaStream = ref<MediaStream | null>(null)
const recordChunks = ref<Blob[]>([])
let recordTimer: number | undefined

/** 探测浏览器支持的录音格式（iOS Safari 仅 mp4/AAC，Android/桌面 Chrome 优先 webm;opus） */
const AUDIO_MIME =
  (['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/wav'] as const).find((m) =>
    MediaRecorder.isTypeSupported(m),
  ) ?? ''

// 是否为空态（无会话或无消息）
const isWelcome = computed(() => !currentSessionId.value || messages.value.length === 0)

// ---------- 生命周期 ----------
onMounted(async () => {
  await loadSessions()
})

onBeforeUnmount(() => {
  aborter.value?.abort()
  // 停止录音并释放麦克风
  mediaRecorder.value?.stop()
  mediaStream.value?.getTracks().forEach((t) => t.stop())
  window.clearTimeout(recordTimer)
  // 清理 body 滚动锁（以防卸载时 drawer 开着）
  document.body.style.overflow = ''
})

// ---------- 移动端 drawer 开关 + body 滚动锁 ----------
function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

function closeDrawer() {
  drawerOpen.value = false
}

watch(drawerOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
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
  aborter.value?.abort()
  currentSessionId.value = id
  messages.value = []
  closeDrawer()
  await loadMessages()
  scrollToBottom()
}

/** 进入本地草稿态（不调 API，首条消息发送时后端原子创建） */
function newDraft() {
  aborter.value?.abort()
  currentSessionId.value = null
  messages.value = []
  inputText.value = ''
  closeDrawer()
  void nextTick(() => inputEl.value?.focus())
}

async function loadMessages() {
  if (!currentSessionId.value) return
  try {
    const raw = await assistantApi.messages(currentSessionId.value)
    // 收集所有 tool_result 消息，按 planId 索引（合并进确认卡，不单独渲染）
    const results = new Map<string, { kind: string; content: string }>()
    for (const m of raw) {
      const meta = (m.meta ?? {}) as Record<string, unknown>
      if (m.type === 'tool_result' && typeof meta.planId === 'string') {
        results.set(meta.planId, { kind: String(meta.kind ?? 'executed'), content: m.content })
      }
    }
    messages.value = raw
      .filter((m) => m.type !== 'tool_result') // 结果合并进 confirm_request 消息，跳过独立渲染
      .map((m) => {
        const meta = (m.meta ?? {}) as Record<string, unknown>
        const um: UIMessage = { ...m }
        if (m.type === 'confirm_request' && typeof meta.planId === 'string') {
          const done = results.get(meta.planId)
          if (done) {
            um.confirmResult = {
              state: done.kind === 'executed' ? 'executed' : done.kind === 'cancelled' ? 'cancelled' : 'failed',
              message: done.content,
            }
          } else {
            um.pendingPlan = { planId: meta.planId, summary: typeof meta.summary === 'string' ? meta.summary : '' }
          }
        }
        return um
      })
    await nextTick(() => scrollToBottom())
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载消息失败'
  }
}

// ---------- 发送消息 + SSE 流式接收 ----------
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value) return

  sending.value = true
  error.value = ''
  const wasDraft = currentSessionId.value === null

  inputText.value = ''

  // 追加用户消息
  const userMsg: UIMessage = { id: `user-${Date.now()}`, role: 'user', content: text }
  messages.value.push(userMsg)

  // 创建 assistant 占位消息（push 后取代理引用：直接改局部对象不会触发 Vue 响应式）
  messages.value.push({
    id: `ai-${Date.now()}`,
    role: 'assistant',
    content: '',
    streaming: true,
  })
  const aiMsg = messages.value[messages.value.length - 1]!
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
          if (wasDraft) {
            const created = evt.sessionId
            if (!sessions.value.some((s) => s.id === created)) {
              sessions.value.unshift({ id: created, title: text.slice(0, 20), updatedAt: new Date().toISOString() })
            }
            if (currentSessionId.value === null) currentSessionId.value = created
          }
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
    const target = messages.value.find((m) => m.pendingPlan?.planId === planId)
    if (target) {
      const state = !approved ? 'cancelled' : result.ok ? 'executed' : 'failed'
      target.pendingPlan = undefined
      target.confirmResult = { state, message: result.message }
    }
    refreshSessionsSilent()
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      const target = messages.value.find((m) => m.pendingPlan?.planId === planId)
      if (target) {
        target.pendingPlan = undefined
        target.confirmResult = { state: 'failed', message: '计划已过期，请重新说一遍' }
      }
    } else {
      error.value = e instanceof Error ? e.message : '操作失败'
    }
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

// ---------- 语音输入：录音 → 上传 → 填入输入框 ----------
function toggleRecording() {
  if (isRecording.value) {
    mediaRecorder.value?.stop()
    // onstop 里自动调用 uploadRecording
    window.clearTimeout(recordTimer)
    mediaStream.value?.getTracks().forEach((t) => t.stop())
    return
  }

  // 开始录音
  error.value = ''
  void (async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStream.value = stream
      recordChunks.value = []
      const rec = new MediaRecorder(stream, AUDIO_MIME ? { mimeType: AUDIO_MIME } : undefined)
      mediaRecorder.value = rec
      rec.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) recordChunks.value.push(e.data)
      }
      rec.onstop = () => {
        void uploadRecording()
      }
      rec.start()
      isRecording.value = true
      // 60s 上限自动停止
      recordTimer = window.setTimeout(() => {
        if (isRecording.value) toggleRecording()
      }, 60_000)
    } catch (e: unknown) {
      error.value =
        e instanceof DOMException && e.name === 'NotAllowedError'
          ? '麦克风权限被拒绝，请在浏览器设置中允许'
          : '无法访问麦克风'
    }
  })()
}

async function uploadRecording() {
  isRecording.value = false
  window.clearTimeout(recordTimer)
  if (recordChunks.value.length === 0) return
  const type = AUDIO_MIME || 'audio/webm'
  const blob = new Blob(recordChunks.value, { type })
  const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : type.includes('wav') ? 'wav' : 'webm'
  recordChunks.value = []
  transcribing.value = true
  try {
    const fd = new FormData()
    fd.append('file', blob, `voice.${ext}`)
    const res = await fetch('/api/transcribe', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken() ?? ''}` },
      body: fd,
    })
    const env = (await res.json()) as { code: number; message: string; data?: { text?: string } }
    if (env.code !== 200) throw new Error(env.message || '转写失败')
    const text = (env.data?.text ?? '').trim()
    if (text) inputText.value = text // 填入输入框，不自动发送
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '语音识别失败'
  } finally {
    transcribing.value = false
  }
}

/** 删除会话（两段式确认） */
async function onDeleteSession(s: AssistantSession) {
  if (delConfirmId.value !== s.id) {
    delConfirmId.value = s.id
    window.setTimeout(() => {
      if (delConfirmId.value === s.id) delConfirmId.value = null
    }, 3000)
    return
  }
  delConfirmId.value = null
  try {
    await assistantApi.deleteSession(s.id)
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
    if (currentSessionId.value === s.id) {
      aborter.value?.abort()
      currentSessionId.value = null
      messages.value = []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除会话失败'
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

// ---------- 时间格式化 ----------
function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

// ---------- watch 会话变化 → 刷新会话列表（标题实时更新） ----------
watch(currentSessionId, () => {
  void refreshSessionsSilent()
})
</script>

<template>
  <div class="assistant-page">
    <div class="chat-layout">
      <!-- ═══ 左侧会话栏（桌面端 flex 子项，手机端 fixed 抽屉） ═══ -->
      <aside class="session-sidebar" :class="{ 'is-open': drawerOpen }">
        <div class="sidebar-inner">
          <!-- 新对话按钮 -->
          <button
            class="new-session-btn"
            :class="{ 'is-active': !loading && currentSessionId === null }"
            @click="newDraft"
            title="新对话"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="new-session-icon">
              <path d="M12 5v14M5 12h14" />
            </svg>
            <span>新对话</span>
          </button>

          <!-- 会话列表 -->
          <div class="session-list">
            <button
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ 'is-active': s.id === currentSessionId }"
              @click="selectSession(s.id)"
            >
              <span class="session-title">{{ sessionLabel(s) }}</span>
              <span class="session-time">{{ formatTime(s.updatedAt) }}</span>
              <span
                class="session-del"
                role="button"
                tabindex="0"
                :class="{ 'is-confirm': delConfirmId === s.id }"
                @click.stop="onDeleteSession(s)"
                @keydown.enter.stop="onDeleteSession(s)"
                aria-label="删除会话"
              >
                <svg
                  v-if="delConfirmId !== s.id"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="session-del-icon"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
                <span v-else class="session-del-confirm">确认？</span>
              </span>
            </button>

            <!-- 空会话提示 -->
            <div v-if="!loading && sessions.length === 0" class="session-empty">
              暂无会话，点击上方按钮开始
            </div>
          </div>
        </div>
      </aside>

      <!-- ═══ 抽屉遮罩（仅手机端） ═══ -->
      <Transition name="backdrop">
        <div v-if="drawerOpen" class="drawer-backdrop" @click="closeDrawer" aria-label="关闭会话列表"></div>
      </Transition>

      <!-- ═══ 右侧聊天区 ═══ -->
      <div class="chat-area">
        <!-- 手机端顶部栏（汉堡按钮） -->
        <div class="mobile-top-bar">
          <button class="hamburger-btn" @click="toggleDrawer" aria-label="会话列表">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="hamburger-icon">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <span class="mobile-title">AI 助手</span>
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

                  <!-- 执行结果卡片 -->
                  <div v-else-if="m.confirmResult" class="confirm-result" :class="'is-' + m.confirmResult.state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="confirm-result-icon">
                      <path v-if="m.confirmResult.state === 'executed'" d="M20 6 9 17l-5-5" />
                      <path v-else-if="m.confirmResult.state === 'cancelled'" d="M9 9l6 6M15 9l-6 6" />
                      <path v-else d="M12 9v4M12 17h.01" />
                    </svg>
                    <span class="confirm-result-text">{{ m.confirmResult.message }}</span>
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
              ref="inputEl"
              v-model="inputText"
              class="input-field"
              placeholder="用一句话记账，比如：昨天午饭花了 68"
              :disabled="sending"
              rows="1"
              @keydown="onKeydown"
            ></textarea>
            <button
              class="mic-btn"
              :class="{ 'is-recording': isRecording }"
              :disabled="transcribing || sending"
              @click="toggleRecording"
              :title="isRecording ? '停止录音' : '语音输入'"
              aria-label="语音输入"
            >
              <svg v-if="!isRecording" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mic-icon">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" x2="12" y1="19" y2="22" />
              </svg>
              <span v-else class="mic-rec-dot"></span>
            </button>
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
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════════════
   assistant page — Apple Liquid Glass 两栏布局
   ════════════════════════════════════════════════════════════ */

/* ── 页面容器：桌面端作为 .content flex 子项填满剩余空间，移动端自适应 ── */
.assistant-page {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── 两栏布局 ── */
.chat-layout {
  display: flex;
  height: 100%;
  position: relative;
}

/* ═══ 左侧会话栏 ═══ */
.session-sidebar {
  flex: 0 0 250px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--hairline);
  background: var(--surface);
  overflow: hidden;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px 10px 10px;
}

/* ── 新对话按钮 ── */
.new-session-btn {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  margin: 0 4px 12px;
  padding: 10px 16px;
  border: 0;
  border-radius: var(--r-pill);
  background: var(--accent);
  color: #fff;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 113, 227, 0.25);
  transition: opacity 160ms ease, box-shadow 200ms var(--ease-out-quart);
}

.new-session-btn:hover {
  box-shadow: 0 4px 14px rgba(0, 113, 227, 0.32);
}

.new-session-btn:active {
  opacity: 0.88;
}

.new-session-btn.is-active {
  background: #005bbf;
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.2), 0 2px 8px rgba(0, 113, 227, 0.25);
}

.new-session-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}

/* ── 会话列表 ── */
.session-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 44px;
  padding: 10px 12px;
  border: 0;
  border-radius: var(--r-thumb);
  background: transparent;
  color: var(--text);
  font-size: 0.86rem;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: background 160ms ease, color 160ms ease;
  position: relative;
}

.session-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
  transition: height 200ms var(--ease-out-quart);
}

.session-item:hover {
  background: var(--hover);
}

.session-item.is-active {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.08);
}

.session-item.is-active::before {
  height: 18px;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.session-time {
  flex: 0 0 auto;
  color: var(--text-4);
  font-size: 0.72rem;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}

.session-item.is-active .session-time {
  color: var(--accent);
  opacity: 0.7;
}

/* ── 会话删除按钮 ── */
.session-del {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  min-height: 28px;
  padding: 4px;
  border-radius: var(--r-thumb);
  color: var(--text-4);
  opacity: 0.65;
  cursor: pointer;
  transition: opacity 160ms ease, color 160ms ease, background 160ms ease;
}

/* 触屏（无 hover）常显删除按钮；仅悬停设备默认隐藏、hover 会话项时显示 */
@media (hover: hover) {
  .session-del {
    opacity: 0;
  }

  .session-item:hover .session-del {
    opacity: 0.65;
  }
}

.session-del:hover {
  opacity: 1 !important;
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.06);
}

.session-del-icon {
  width: 13px;
  height: 13px;
}

.session-del.is-confirm {
  opacity: 1 !important;
  color: var(--heat);
  background: rgba(255, 107, 0, 0.08);
}

.session-del-confirm {
  font-size: 0.65rem;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1;
}

.session-empty {
  padding: 24px 12px;
  text-align: center;
  color: var(--text-4);
  font-size: 0.82rem;
  line-height: 1.55;
}

/* ═══ 抽屉遮罩（仅手机端显示） ═══ */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(0, 0, 0, 0.32);
  /* backdrop-filter 由 Vue Transition 控制 */
}

.backdrop-enter-active {
  transition: opacity 280ms ease;
}

.backdrop-leave-active {
  transition: opacity 220ms ease;
}

.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

/* ═══ 右侧聊天区 ═══ */
.chat-area {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── 手机端顶部栏（仅 ≤860px 显示） ── */
.mobile-top-bar {
  display: none;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--hairline);
  background: var(--surface);
}

.hamburger-btn {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--r-thumb);
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
  transition: background 160ms ease;
}

.hamburger-btn:hover {
  background: var(--hover);
}

.hamburger-icon {
  width: 20px;
  height: 20px;
}

.mobile-title {
  font-size: 0.96rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}

/* ═══ 消息区域 ═══ */
.msg-area {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 20px var(--pad-x) 16px;
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

/* ── 确认结果卡片（确认/取消后原地显示） ── */
.confirm-result {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--r-thumb);
  background: var(--surface);
  box-shadow: var(--sh-card);
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.confirm-result-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  margin-top: 1px;
}

.confirm-result-text {
  font-size: 0.88rem;
  font-weight: 500;
  line-height: 1.55;
  color: var(--text);
  word-break: break-word;
}

.confirm-result.is-executed .confirm-result-icon,
.confirm-result.is-executed .confirm-result-text {
  color: var(--live);
}

.confirm-result.is-cancelled .confirm-result-icon,
.confirm-result.is-cancelled .confirm-result-text {
  color: var(--text-3);
}

.confirm-result.is-failed .confirm-result-icon,
.confirm-result.is-failed .confirm-result-text {
  color: var(--heat);
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
  /* Apple：输入容器用 card 级圆角矩形（r-pill 大胶囊 + spread 光晕会渲染出矩形撕裂感） */
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-card);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.input-row:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
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

/* 覆盖全局 textarea:focus 的 4px 直角光晕（style.css 焦点环）：
   聚焦反馈由容器 .input-row:focus-within 提供（贴合圆角，无矩形撕裂感） */
.input-field:focus {
  box-shadow: none;
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

/* ── 麦克风按钮 ── */
.mic-btn {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease;
}

.mic-btn:hover:not(:disabled) {
  color: var(--text);
  background: var(--hover);
}

.mic-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.mic-icon {
  width: 18px;
  height: 18px;
}

/* 录音中：红色脉冲 */
.mic-btn.is-recording {
  color: var(--heat);
  background: transparent;
}

.mic-btn.is-recording:hover:not(:disabled) {
  background: rgba(255, 107, 0, 0.08);
}

.mic-rec-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--heat);
  animation: mic-pulse 1s ease-in-out infinite;
}

@keyframes mic-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: .5; transform: scale(.8); }
}

/* ═══ 消息入场动效（轻量淡入） ═══ */
.msg-enter-active {
  transition: opacity 280ms var(--ease-out-quart), transform 280ms var(--ease-out-quart);
}

.msg-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

/* ════════════════════════════════════════════════════════════
   响应式 — 手机端 ≤860px
   ════════════════════════════════════════════════════════════ */

@media (max-width: 860px) {
  .assistant-page {
    height: 100%;
  }

  .chat-layout {
    flex-direction: column;
  }

  /* 侧栏变为固定抽屉 */
  .session-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 200;
    width: 280px;
    flex: none;
    border-right: 1px solid var(--hairline);
    box-shadow: var(--sh-overlay);
    transform: translateX(-100%);
    transition: transform 300ms var(--ease-spring);
  }

  .session-sidebar.is-open {
    transform: translateX(0);
  }

  /* 显示手机端顶部栏 */
  .mobile-top-bar {
    display: flex;
  }

  /* 聊天区撑满 */
  .chat-area {
    flex: 1 1 auto;
  }

  .msg-area {
    padding: 16px 12px;
  }

  .input-bar {
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px));
  }

  .msg-bubble {
    max-width: 90%;
  }
}

/* ════════════════════════════════════════════════════════════
   可访问性：减少动效 / 透明度 / 对比度
   ════════════════════════════════════════════════════════════ */

@media (prefers-reduced-motion: reduce) {
  .stream-cursor { animation: none; }
  .msg-enter-active { transition: opacity 150ms ease; }
  .msg-enter-from { transform: none; }
  .session-sidebar { transition: opacity 200ms ease; }
  .session-sidebar:not(.is-open) { opacity: 0; }
  .session-item::before { transition: none; }
  .mic-rec-dot { animation: none; }
}

@media (prefers-reduced-transparency: reduce) {
  .drawer-backdrop { background: rgba(0, 0, 0, 0.48); }
}

@media (prefers-contrast: more) {
  .input-row { border-color: rgba(0,0,0,0.35); }
  .confirm-card { border-color: rgba(0,0,0,0.25); }
  .session-sidebar { border-right-color: rgba(0,0,0,0.18); }
}
</style>
