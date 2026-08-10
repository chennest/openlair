import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type AssistantSession,
  type AssistantMessage,
  nextId,
  respond,
  ok,
  err,
  guard,
  type MockReq,
} from './store'

// ---------- 金额匹配 ----------
function extractAmount(msg: string): number {
  const m = msg.match(/(\d+(?:\.\d{1,2})?)\s*(?:元|块|$)|\$(?:\d+(?:\.\d{1,2})?|\d+)/)
  if (m) return Number.parseFloat(m[1] || m[0].slice(1)) || 68
  return 68
}

function guessCategory(msg: string): string {
  if (/吃|饭|餐|外卖|面|粉|火锅|烧烤|奶茶|饮料/i.test(msg)) return '餐饮'
  if (/车|打车|交通|地铁|公交|油|高速|停车/i.test(msg)) return '交通'
  if (/工资|收入|收到|转账|进账/i.test(msg)) return '工资'
  if (/购物|买|淘宝|京东/i.test(msg)) return '购物'
  if (/房|租|水电|物业/i.test(msg)) return '居住'
  if (/电影|游戏|娱乐|KTV/i.test(msg)) return '娱乐'
  return '餐饮'
}

function guessType(msg: string): '支出' | '收入' {
  return /工资|收入|收到|转账|进账|奖金|理财|礼金|退款/i.test(msg) ? '收入' : '支出'
}

// ---------- 辅助 ----------
function nowISO(): string {
  return new Date().toISOString()
}

export default {
  // 会话列表
  sessions: defineMock({
    url: '/api/assistant/sessions',
    method: 'GET',
    response: respond(
      guard((_req) => ok(
        store.assistantSessions
          .filter((s) => store.assistantMessages.some((m) => m.sessionId === s.id))
          .slice()
          .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
      )),
    ),
  }),

  // 新建会话
  createSession: defineMock({
    url: '/api/assistant/sessions',
    method: 'POST',
    response: respond(
      guard(() => {
        const t = nowISO()
        const s: AssistantSession = {
          id: nextId(store.assistantSessions),
          title: '新对话',
          createdAt: t,
          updatedAt: t,
        }
        store.assistantSessions.push(s)
        return ok({ id: s.id, title: s.title, updatedAt: s.updatedAt })
      }),
    ),
  }),

  // 删除会话
  deleteSession: defineMock({
    url: '/api/assistant/sessions/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const sid = Number(req.params?.id)
        const idx = store.assistantSessions.findIndex((s) => s.id === sid)
        if (idx === -1) return err(404, '会话不存在')
        store.assistantSessions.splice(idx, 1)
        store.assistantMessages = store.assistantMessages.filter((m) => m.sessionId !== sid)
        return ok({ ok: true })
      }),
    ),
  }),

  // 获取会话消息
  messages: defineMock({
    url: '/api/assistant/sessions/:id/messages',
    method: 'GET',
    response: respond(
      guard((req) => {
        const sid = Number(req.params?.id)
        const msgs = store.assistantMessages
          .filter((m) => m.sessionId === sid)
          .sort((a, b) => a.id - b.id)
        return ok(msgs.map((m) => ({
          id: m.id,
          role: m.role,
          type: m.type,
          content: m.content,
          meta: m.meta,
          createdAt: m.createdAt,
        })))
      }),
    ),
  }),

  // 确认/取消记账
  confirm: defineMock({
    url: '/api/assistant/confirm',
    method: 'POST',
    response: respond(
      guard((req) => {
        const { planId, approved } = req.body ?? {}
        if (!planId) return err(400, '缺少 planId')

        // 解析 planId 里的临时数据：planId 格式 "plan_<数字>_<金额>_<分类id>_<类型>"
        // 实际从 planId 提取不到时用默认值
        const parts = String(planId).split('_')
        const amount = Number(parts[2]) || 68
        const categoryId = Number(parts[3]) || 1
        const type = parts[4] === 'income' ? '收入' : '支出'
        const cat = store.categories.find((c) => c.id === categoryId)
        const catName = cat?.name ?? '餐饮'

        if (approved) {
          const t = nowISO()
          const today = new Date().toISOString().slice(0, 10)
          store.transactions.push({
            id: nextId(store.transactions),
            type: type as '支出' | '收入',
            categoryId,
            bookId: 1,
            userId: 1,
            amount: Number(amount.toFixed(2)),
            date: today,
            note: `AI 助手记账`,
            createdAt: t,
            updatedAt: t,
          })
          const executedContent = `已记账：${type} ${amount.toFixed(2)} 元 · ${catName}`
          const sid = Number(parts[1]) || 0
          store.assistantMessages.push({
            id: nextId(store.assistantMessages),
            sessionId: sid,
            role: 'assistant',
            type: 'tool_result',
            content: executedContent,
            meta: {
              planId: String(planId),
              kind: 'executed',
              summary: `${type} ${amount.toFixed(2)} 元 · 分类 ${catName}`,
            },
            createdAt: nowISO(),
          })
          return ok({ ok: true, message: executedContent })
        }
        const sid = Number(parts[1]) || 0
        store.assistantMessages.push({
          id: nextId(store.assistantMessages),
          sessionId: sid,
          role: 'assistant',
          type: 'tool_result',
          content: '已取消本次记账',
          meta: { planId: String(planId), kind: 'cancelled', summary: '已取消本次记账' },
          createdAt: nowISO(),
        })
        return ok({ ok: true, message: '已取消本次记账' })
      }),
    ),
  }),

  // 流式聊天（SSE）— 原始响应
  chat: defineMock({
    url: '/api/assistant/chat',
    method: 'POST',
    response: (req: MockReq, res: {
      statusCode: number
      setHeader: (name: string, value: string) => void
      write: (chunk: string) => void
      end: (body?: string) => void
    }) => {
      // 鉴权检查
      const authHeader = req.headers?.authorization
      if (typeof authHeader !== 'string' || !authHeader.startsWith('Bearer ')) {
        res.statusCode = 401
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        res.end(JSON.stringify({ code: 401, message: '未登录或登录已过期，请重新登录', data: null }))
        return
      }

      const { sessionId, message } = (req.body ?? {}) as { sessionId?: number | null; message?: string }
      if (!message) {
        res.statusCode = 400
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        res.end(JSON.stringify({ code: 400, message: '缺少 message', data: null }))
        return
      }

      // 未指定会话时自动创建新会话
      let sid = sessionId
      if (!sid) {
        const t = nowISO()
        const s: AssistantSession = {
          id: nextId(store.assistantSessions),
          title: '新对话',
          createdAt: t,
          updatedAt: t,
        }
        store.assistantSessions.push(s)
        sid = s.id
      }

      // 存储用户消息
      const userMsg: AssistantMessage = {
        id: nextId(store.assistantMessages),
        sessionId: sid,
        role: 'user',
        content: message,
        createdAt: nowISO(),
      }
      store.assistantMessages.push(userMsg)

      // 更新会话标题（用截取的预览文本）
      const session = store.assistantSessions.find((s) => s.id === sid)
      if (session) {
        session.title = message.slice(0, 20)
        session.updatedAt = nowISO()
      }

      const amount = extractAmount(message)
      const category = guessCategory(message)
      const type = guessType(message)
      const cat = store.categories.find(
        (c) => c.name === category && (type === '收入' ? c.type === '收入' : c.type === '支出'),
      )
      const categoryId = cat?.id ?? 1
      const typeLabel = type === '收入' ? '收入' : '支出'
      const planId = `plan_${sid}_${amount}_${categoryId}_${type === '收入' ? 'income' : 'expense'}`

      // SSE 响应头
      res.statusCode = 200
      res.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
      res.setHeader('Cache-Control', 'no-cache')
      res.setHeader('Connection', 'keep-alive')
      res.setHeader('X-Accel-Buffering', 'no')

      // 模拟流式返回
      const chunks = [
        `好的，我来帮你记一笔：\n`,
        `${typeLabel} ${amount.toFixed(2)} 元，`,
        `分类「${category}」`,
      ]

      let delay = 300
      let chunkIdx = 0
      let fullContent = ''

      function sendNext() {
        if (chunkIdx < chunks.length) {
          const delta = chunks[chunkIdx]
          fullContent += delta
          res.write(`data: ${JSON.stringify({ type: 'message_delta', delta })}\n\n`)
          chunkIdx++
          setTimeout(sendNext, delay)
          delay += 120
        } else {
          // 发送 confirm_request
          res.write(
            `data: ${JSON.stringify({
              type: 'confirm_request',
              planId,
              tool: 'LedgerPlan',
              summary: `${typeLabel} ${amount.toFixed(2)} 元 · 分类 ${category}`,
            })}\n\n`,
          )
          // 再等一下发送 done
          setTimeout(() => {
            res.write(`data: ${JSON.stringify({ type: 'done', sessionId: sid })}\n\n`)

            // 把 AI 的消息内容和待确认状态存起来
            const aiMsg: AssistantMessage = {
              id: nextId(store.assistantMessages),
              sessionId: sid,
              role: 'assistant',
              type: 'confirm_request',
              content: fullContent + `\n[待确认] ${typeLabel} ${amount.toFixed(2)} 元 · ${category}`,
              meta: { planId, tool: 'LedgerPlan', summary: `${typeLabel} ${amount.toFixed(2)} 元 · 分类 ${category}` },
              createdAt: nowISO(),
            }
            store.assistantMessages.push(aiMsg)

            res.end()
          }, 200)
        }
      }

      setTimeout(sendNext, 200)
    },
  }),
}
