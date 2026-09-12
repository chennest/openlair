<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Mic, Send, Square, Check, X, Loader2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageFooter,
  MessageHeader,
} from '@/components/ui/message'
import { Bubble } from '@/components/ui/bubble'
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from '@/components/ui/message-scroller'
import {
  assistantApi,
  streamChat,
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

// ---------- 状态（单一持久线程） ----------
const currentSessionId = ref<number | null>(null)
const messages = ref<UIMessage[]>([])
const inputText = ref('')
const loading = ref(true)
const sending = ref(false)
const confirming = ref<string | null>(null) // 正在确认的 planId
const error = ref('')
const aborter = ref<AbortController | null>(null)

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

// 欢迎态建议示例
const examples = [
  { emoji: '💰', text: '记一笔：午饭 68 元' },
  { emoji: '🚕', text: '昨天打车花了 30 元' },
  { emoji: '📊', text: '这个月餐饮花了多少' },
  { emoji: '💼', text: '收到工资 8000 元' },
]

// ---------- 生命周期 ----------
onMounted(async () => {
  await loadThread()
})

onBeforeUnmount(() => {
  aborter.value?.abort()
  // 停止录音并释放麦克风
  mediaRecorder.value?.stop()
  mediaStream.value?.getTracks().forEach((t) => t.stop())
  window.clearTimeout(recordTimer)
})

// ---------- 线程（单一持久线程） ----------
async function loadThread() {
  loading.value = true
  error.value = ''
  try {
    const sessions = await assistantApi.sessions()
    // 取最近会话；无则进入欢迎态，首条消息发送时后端自动创建
    if (sessions.length > 0) {
      currentSessionId.value = sessions[0].id
      await loadMessages()
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载会话失败'
  } finally {
    loading.value = false
  }
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
          if (wasDraft) currentSessionId.value = evt.sessionId
          break
        case 'error':
          aiMsg.content += aiMsg.content ? `\n\n⚠️ ${evt.message}` : `⚠️ ${evt.message}`
          aiMsg.streaming = false
          streamDone = true
          break
      }
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

/** 停止生成：中止当前 SSE 流 */
function stopGeneration() {
  aborter.value?.abort()
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
    // 取消时后端会追加一条 AI 追问（复述 + 工具用途 + 问要不要改）
    if (!approved && result.followUp) {
      messages.value.push({ id: `ai-${Date.now()}`, role: 'assistant', content: result.followUp })
    }
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
    const res = await fetch('/api/assistant/transcribe', {
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

// ---------- 工具方法 ----------
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

// 消息时间格式化（footer 展示）
function formatTime(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <MessageScrollerProvider auto-scroll default-scroll-position="last-anchor">
      <MessageScroller class="flex min-h-0 flex-1 flex-col">
        <MessageScrollerViewport class="flex-1 overflow-y-auto">
          <div class="mx-auto flex h-full w-full max-w-2xl flex-col px-4 py-6 sm:px-6">
            <!-- 加载中 -->
            <div v-if="loading" class="grid flex-1 place-items-center">
              <div class="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 class="size-4 animate-spin" />
                正在加载…
              </div>
            </div>

            <!-- 加载失败 -->
            <div v-else-if="error && !currentSessionId" class="grid flex-1 place-items-center">
              <Card class="w-full max-w-sm">
                <CardContent class="flex flex-col items-center gap-2 pt-6 text-center">
                  <p class="text-sm font-medium text-destructive">{{ error }}</p>
                </CardContent>
              </Card>
            </div>

            <!-- 欢迎态 -->
            <div v-else-if="isWelcome" class="grid flex-1 place-items-center">
              <div class="w-full max-w-lg text-center">
                <div class="mx-auto mb-6 grid size-16 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="size-8">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    <path d="M8 10h8M8 13h5" />
                  </svg>
                </div>
                <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">你好，我来帮你记账</h1>
                <p class="mt-2 text-sm text-muted-foreground">用一句话记账、查账，AI 自动识别分类与金额</p>
                <div class="mt-8 grid gap-3 sm:grid-cols-2">
                  <Button
                    v-for="q in examples"
                    :key="q.text"
                    variant="outline"
                    class="h-auto justify-start gap-3 px-4 py-3.5 text-left text-sm font-medium"
                    @click="onExample(q.text)"
                  >
                    <span class="text-base" aria-hidden="true">{{ q.emoji }}</span>
                    <span class="truncate">{{ q.text }}</span>
                  </Button>
                </div>
              </div>
            </div>

            <!-- 消息列表 -->
            <MessageScrollerContent v-else class="flex flex-col gap-5 pb-2">
              <MessageScrollerItem
                v-for="m in messages"
                :key="m.id"
                :message-id="String(m.id)"
                :scroll-anchor="m.role === 'user'"
              >
                <Message :align="m.role === 'user' ? 'end' : 'start'">
                  <MessageAvatar>
                    <Avatar v-if="m.role === 'assistant'" class="size-8">
                      <AvatarFallback class="bg-primary text-primary-foreground text-xs font-semibold">AI</AvatarFallback>
                    </Avatar>
                  </MessageAvatar>

                  <MessageContent>
                    <MessageHeader class="text-xs text-muted-foreground">
                      <template v-if="m.role === 'user'">我</template>
                      <template v-else>OpenLair 助手</template>
                      <span v-if="formatTime(m.createdAt)" class="font-normal opacity-70">{{ formatTime(m.createdAt) }}</span>
                    </MessageHeader>

                    <!-- 用户消息：primary 气泡右对齐 -->
                    <Bubble
                      v-if="m.role === 'user'"
                      :align="'end'"
                      variant="default"
                      class="bg-primary text-primary-foreground rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
                    >
                      <span class="whitespace-pre-wrap break-words">{{ m.content }}</span>
                    </Bubble>

                    <!-- AI 消息：ghost 无框正文 -->
                    <Bubble v-else :align="'start'" variant="ghost" class="rounded-2xl px-1 py-0.5 text-sm leading-relaxed">
                      <span class="whitespace-pre-wrap break-words text-foreground">{{ m.content }}</span>
                      <span v-if="m.streaming" class="stream-cursor ml-0.5 inline-block" aria-label="AI 正在输入">|</span>
                    </Bubble>

                    <!-- 确认卡片 -->
                    <Card v-if="m.pendingPlan" class="mt-3 w-fit max-w-full">
                      <CardHeader class="gap-1.5 p-4 pb-0">
                        <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                          <Loader2 class="size-4 text-primary" />
                          确认记账
                        </CardTitle>
                        <CardDescription class="text-xs leading-relaxed">{{ m.pendingPlan.summary }}</CardDescription>
                      </CardHeader>
                      <CardContent class="flex gap-2 p-4">
                        <Button
                          variant="outline"
                          size="sm"
                          class="flex-1"
                          :disabled="confirming === m.pendingPlan.planId"
                          @click="handleConfirm(m.pendingPlan!.planId, false)"
                        >
                          <X class="size-3.5" />
                          {{ confirming === m.pendingPlan.planId ? '处理中…' : '取消' }}
                        </Button>
                        <Button
                          size="sm"
                          class="flex-1"
                          :disabled="confirming === m.pendingPlan.planId"
                          @click="handleConfirm(m.pendingPlan!.planId, true)"
                        >
                          <Check class="size-3.5" />
                          {{ confirming === m.pendingPlan.planId ? '处理中…' : '确认' }}
                        </Button>
                      </CardContent>
                    </Card>

                    <!-- 执行结果卡片 -->
                    <Card v-else-if="m.confirmResult" class="mt-3 w-fit max-w-full" :class="{
                      'border-green-200 bg-green-50': m.confirmResult.state === 'executed',
                      'border-red-200 bg-red-50': m.confirmResult.state === 'failed',
                    }">
                      <CardContent class="flex items-center gap-2 p-3.5 text-sm font-medium"
                        :class="{
                          'text-green-700': m.confirmResult.state === 'executed',
                          'text-muted-foreground': m.confirmResult.state === 'cancelled',
                          'text-red-600': m.confirmResult.state === 'failed',
                        }">
                        <Check v-if="m.confirmResult.state === 'executed'" class="size-4 shrink-0" />
                        <X v-else-if="m.confirmResult.state === 'cancelled'" class="size-4 shrink-0" />
                        <span v-else class="text-destructive">!</span>
                        <span class="break-words">{{ m.confirmResult.message }}</span>
                      </CardContent>
                    </Card>

                    <MessageFooter class="mt-1 text-xs text-muted-foreground">
                      <span v-if="m.streaming" class="flex items-center gap-1.5">
                        <Loader2 class="size-3 animate-spin" />
                        正在生成…
                      </span>
                    </MessageFooter>
                  </MessageContent>
                </Message>
              </MessageScrollerItem>
            </MessageScrollerContent>
          </div>
        </MessageScrollerViewport>
        <MessageScrollerButton direction="end" />
      </MessageScroller>
    </MessageScrollerProvider>

    <!-- 底部输入区 -->
    <div class="flex-0 border-t bg-background px-4 py-3 sm:px-6">
      <div class="mx-auto w-full max-w-2xl">
        <div class="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-ring/30">
          <Textarea
            v-model="inputText"
            class="max-h-32 min-h-0 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-sm leading-relaxed shadow-none focus-visible:ring-0"
            placeholder="用一句话记账，比如：昨天午饭花了 68"
            :disabled="sending"
            rows="1"
            @keydown="onKeydown"
          />
          <Button
            variant="ghost"
            size="icon"
            class="shrink-0 rounded-full text-muted-foreground"
            :class="{ 'text-red-500': isRecording }"
            :disabled="transcribing || sending"
            :title="isRecording ? '停止录音' : '语音输入'"
            aria-label="语音输入"
            @click="toggleRecording"
          >
            <span v-if="!isRecording" class="relative grid place-items-center">
              <Mic class="size-4" />
            </span>
            <span v-else class="mic-rec-dot" aria-hidden="true"></span>
          </Button>
          <Button
            v-if="!sending"
            size="icon"
            class="size-9 shrink-0 rounded-full"
            :disabled="!inputText.trim()"
            aria-label="发送消息"
            @click="sendMessage"
          >
            <Send class="size-4" />
          </Button>
          <Button
            v-else
            size="icon"
            variant="secondary"
            class="size-9 shrink-0 rounded-full"
            aria-label="停止生成"
            title="停止生成"
            @click="stopGeneration"
          >
            <Square class="size-3.5 fill-current" />
          </Button>
        </div>
        <p class="mt-1.5 text-center text-xs text-muted-foreground/70">Enter 发送 · Shift + Enter 换行</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════════════
   assistant page — shadcn-vue demo（vega 风格）
   滚动行为由 MessageScroller 接管（流式跟随 / 上滑释放 / 回合锚定）
   ════════════════════════════════════════════════════════════ */

/* 流式光标 */
.stream-cursor {
  animation: blink 800ms steps(1, end) infinite;
  color: var(--primary);
  font-weight: 300;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 录音中：红色脉冲 */
.mic-rec-dot {
  display: block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--destructive);
  animation: mic-pulse 1s ease-in-out infinite;
}

@keyframes mic-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: .5; transform: scale(.8); }
}

@media (prefers-reduced-motion: reduce) {
  .stream-cursor { animation: none; }
  .mic-rec-dot { animation: none; }
}
</style>
