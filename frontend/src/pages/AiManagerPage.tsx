import { useEffect, useRef, useState } from 'react'
import { ArrowUpOutlined, FileTextOutlined, GlobalOutlined, HistoryOutlined, PlusOutlined, RobotOutlined } from '@ant-design/icons'
import { Button, Input, Spin } from 'antd'
import { getConversations, getMessages, streamChat, type ChatMessage, type Conversation } from '../lib/chat'

const suggestions = [
  '产品品类多，生产资料一大堆，如何利用软小筑快速找到生产信息？',
  '怎么维护我的知识库才能在软小筑轻松的写一份合同？',
  '如何搭建我的智能客服应用？',
  '我创建的文档，其他同事可以看到吗？',
  '怎么才能快速的把我现有的资料一次性放到知识库中？',
  '支持在线编辑吗？',
  '文件一个个传太麻烦！软小筑支持上传文件夹吗？',
]

export function AiManagerPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<string>()
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string>()
  const [toolStatus, setToolStatus] = useState<string>()
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadConversations = async () => {
    try {
      setConversations(await getConversations())
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '加载历史会话失败')
    }
  }

  useEffect(() => { void loadConversations() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, streaming])

  const openConversation = async (id: string) => {
    try {
      setError(undefined)
      setConversationId(id)
      setMessages(await getMessages(id))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '加载会话内容失败')
    }
  }

  const startNewConversation = () => {
    setConversationId(undefined)
    setMessages([])
    setError(undefined)
    setInput('')
  }

  const sendMessage = async (value = input) => {
    const content = value.trim()
    if (!content || streaming) return
    setInput('')
    setError(undefined)
    setToolStatus(undefined)
    setStreaming(true)
    const localUserMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content, created_at: new Date().toISOString() }
    const assistantMessageId = crypto.randomUUID()
    setMessages(previous => [...previous, localUserMessage, { id: assistantMessageId, role: 'assistant', content: '', created_at: new Date().toISOString() }])
    try {
      for await (const event of streamChat(content, conversationId)) {
        if (event.type === 'delta') {
          if (event.conversation_id) setConversationId(event.conversation_id)
          setMessages(previous => previous.map(item => item.id === assistantMessageId ? { ...item, content: `${item.content}${event.delta ?? ''}` } : item))
        }
        if (event.type === 'error') throw new Error(event.detail ?? '生成回复失败')
        if (event.type === 'tool_call') setToolStatus(`正在调用工具：${event.tool ?? '未知工具'}`)
        if (event.type === 'tool_result') setToolStatus(`工具已完成：${event.tool ?? '未知工具'}`)
      }
      await loadConversations()
    } catch (requestError) {
      setMessages(previous => previous.filter(item => item.id !== assistantMessageId || item.content.length > 0))
      setError(requestError instanceof Error ? requestError.message : '生成回复失败')
    } finally {
      setStreaming(false)
    }
  }

  const isWelcome = messages.length === 0
  return <div className="-m-6 flex h-[calc(100vh-48px)] min-h-[680px] bg-white">
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden border-r border-slate-100">
      <div className="flex-1 overflow-y-auto px-8 py-16 lg:px-[15%]">
        {isWelcome ? <div className="mx-auto max-w-[760px]">
          <h1 className="mb-10 text-3xl font-medium text-slate-700">下午好，欢迎使用 AI 管家</h1>
          <div className="mb-9 flex h-44 w-[345px] items-center justify-between rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <div><p className="text-lg font-semibold text-slate-700">新建一个文档</p><p className="mt-1 text-sm text-slate-400">支持 WORD、EXCEL、PPT 等</p></div>
            <FileTextOutlined className="text-5xl text-amber-400" />
          </div>
          <div className="space-y-2">{suggestions.map((suggestion, index) => <button key={suggestion} type="button" onClick={() => void sendMessage(suggestion)} className="block max-w-full rounded-full bg-slate-100 px-4 py-2 text-left text-sm text-slate-600 transition hover:bg-indigo-50 hover:text-indigo-600"><span className="mr-2 text-slate-400">{index + 1}</span><span className="mr-2">🔥</span>{suggestion}</button>)}</div>
        </div> : <div className="mx-auto max-w-[760px] space-y-6">{messages.map(message => <article key={message.id} className={message.role === 'user' ? 'ml-auto max-w-[80%] rounded-2xl bg-indigo-500 px-4 py-3 text-sm leading-7 text-white' : 'max-w-[90%] whitespace-pre-wrap rounded-2xl bg-slate-50 px-5 py-4 text-sm leading-7 text-slate-700'}>{message.content || (streaming && <Spin size="small" />)}</article>)}{toolStatus && <p className="text-sm text-indigo-500">{toolStatus}</p>}<div ref={bottomRef} /></div>}
      </div>
      <div className="px-8 pb-7 lg:px-[15%]">
        {error && <p role="alert" className="mb-3 text-sm text-red-500">{error}</p>}
        <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
          <Input.TextArea value={input} onChange={event => setInput(event.target.value)} onPressEnter={event => { if (!event.shiftKey) { event.preventDefault(); void sendMessage() } }} autoSize={{ minRows: 3, maxRows: 6 }} disabled={streaming} variant="borderless" placeholder="基于知识库提问，Shift + Enter 换行" className="!resize-none !p-1 !text-sm" />
          <div className="mt-2 flex items-center gap-2"><Button size="small" icon={<FileTextOutlined />}>全部资料</Button><Button size="small" type="primary" ghost icon={<RobotOutlined />}>Agent</Button><Button size="small" shape="circle" icon={<GlobalOutlined />} /><Button className="ml-auto" type="primary" shape="circle" aria-label="发送消息" disabled={!input.trim() || streaming} icon={<ArrowUpOutlined />} onClick={() => void sendMessage()} /></div>
        </div>
      </div>
    </section>
    <aside className="hidden w-[285px] shrink-0 bg-white p-5 xl:block">
      <div className="mb-5 flex items-center gap-2 text-base font-semibold text-slate-700"><HistoryOutlined />历史记录</div>
      <Button block icon={<PlusOutlined />} onClick={startNewConversation}>新建会话</Button>
      <p className="mb-3 mt-7 text-xs text-slate-400">最近一周</p>
      <div className="space-y-1">{conversations.map(item => <button key={item.id} type="button" onClick={() => void openConversation(item.id)} className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${conversationId === item.id ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-50'}`}>{item.title}</button>)}</div>
      {conversations.length === 0 && <p className="mt-8 text-center text-sm text-slate-400">暂无历史会话</p>}
    </aside>
  </div>
}
