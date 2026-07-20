import { getStoredAccessToken } from './auth'

const API_BASE = 'http://127.0.0.1:8000'

export type Conversation = {
  id: string
  agent_id: string
  title: string
  updated_at: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  created_at: string
}

type StreamEvent = {
  type: 'delta' | 'tool_call' | 'tool_result' | 'done' | 'error'
  delta?: string
  conversation_id?: string
  message_id?: string
  detail?: string
  tool?: string
  result?: string
}

function authHeaders(): HeadersInit {
  const token = getStoredAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function getConversations(): Promise<Conversation[]> {
  const response = await fetch(`${API_BASE}/api/conversations`, { headers: authHeaders() })
  if (!response.ok) throw new Error('加载历史会话失败')
  const result = await response.json() as { data: Conversation[] }
  return result.data
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, { headers: authHeaders() })
  if (!response.ok) throw new Error('加载会话内容失败')
  const result = await response.json() as { data: ChatMessage[] }
  return result.data
}

export async function* streamChat(message: string, conversationId?: string): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId, agent_id: 'ai-manager' }),
  })
  if (!response.ok || !response.body) throw new Error('发送消息失败')
  if (!response.headers.get('content-type')?.includes('text/event-stream')) {
    throw new Error('后端未返回 SSE 流，请确认 FastAPI 已重启并加载最新代码。')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    const entries = buffer.split('\n\n')
    buffer = entries.pop() ?? ''
    for (const entry of entries) {
      const dataLine = entry.split('\n').find(line => line.startsWith('data: '))
      if (!dataLine) continue
      const event = JSON.parse(dataLine.slice(6)) as StreamEvent
      if (event.type === 'done') completed = true
      yield event
    }
    if (done) break
  }
  if (!completed) throw new Error('SSE 响应未正常结束，请检查后端日志。')
}
