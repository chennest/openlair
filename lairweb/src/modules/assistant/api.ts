import { get, post, del, getToken } from '../../api/request'

// ---------- 类型 ----------

export interface AssistantSession {
  id: number
  title: string
  updatedAt: string
}

export interface AssistantMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  type?: 'text' | 'confirm_request' | 'tool_result'
  meta?: Record<string, unknown>
  createdAt: string
}

/** SSE 事件类型 */
export type ChatEvent =
  | { type: 'message_delta'; delta: string }
  | { type: 'confirm_request'; planId: string; tool: string; summary: string }
  | { type: 'done'; sessionId: number }
  | { type: 'error'; message: string }

export interface ConfirmResult {
  ok: boolean
  message: string
}

// ---------- API ----------

export const assistantApi = {
  /** 会话列表 */
  sessions: () => get<AssistantSession[]>('/api/assistant/sessions'),

  /** 新建会话 */
  createSession: () => post<AssistantSession>('/api/assistant/sessions', {}),

  /** 获取某会话的消息列表 */
  messages: (sessionId: number) => get<AssistantMessage[]>(`/api/assistant/sessions/${sessionId}/messages`),

  /** 确认/取消记账计划 */
  confirm: (planId: string, approved: boolean) =>
    post<ConfirmResult>('/api/assistant/confirm', { planId, approved }),

  /** 删除会话（含消息） */
  deleteSession: (id: number) => del<{ ok: boolean }>(`/api/assistant/sessions/${id}`),
}

/**
 * 流式聊天 —— 原生 fetch + ReadableStream，逐行解析 SSE
 * @param sessionId 会话 id（null 表示新对话草稿，后端自动创建）
 * @param message 用户消息文本
 * @param onEvent 每收到一个 JSON 事件回调
 * @param onError 非 200 或网络错误回调
 * @param signal 用于取消请求
 */
export async function streamChat(
  sessionId: number | null,
  message: string,
  onEvent: (evt: ChatEvent) => void,
  onError: (msg: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken()
  try {
    const res = await fetch('/api/assistant/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ sessionId, message }),
      signal,
    })

    if (!res.ok) {
      let errMsg = `请求失败 (${res.status})`
      try {
        const errBody = await res.json()
        if (errBody?.message) errMsg = errBody.message
      } catch { /* ignore json parse error */ }
      onError(errMsg)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      onError('浏览器不支持流式读取')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 最后一个可能不完整
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(trimmed.slice(6)) as ChatEvent
          onEvent(evt)
        } catch {
          // 非 JSON 行忽略
        }
      }
    }
    // 处理剩余 buffer
    if (buffer.trim().startsWith('data: ')) {
      try {
        const evt = JSON.parse(buffer.trim().slice(6)) as ChatEvent
        onEvent(evt)
      } catch { /* ignore */ }
    }
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    onError(e instanceof Error ? e.message : '网络连接失败')
  }
}
