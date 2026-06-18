import { useState, useEffect, useRef, useCallback } from 'react'
import { gateway } from '../lib/gateway'
import { browserGateway } from '../lib/gateway-browser'

// Auto-detect: Electron IPC vs Browser WebSocket
const gw = window.boboAPI ? gateway : browserGateway
const isBrowserDev = !window.boboAPI

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  text: string
  toolName?: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Connect to backend
  useEffect(() => {
    if (isBrowserDev) {
      gw.connect(9876)  // WebSocket to local ws_server
    } else {
      gw.connect()
    }

    gw.on('gw.ready', async () => {
      setConnected(true)
      // Create a new session
      const result = await gw.call('session.create', { title: 'New Chat' })
      if (result && typeof result === 'object' && 'session_id' in result) {
        const sid = (result as Record<string, unknown>).session_id as string
        setSessionId(sid)
        gw.subscribe(sid)
      }
    })

    // Handle streaming text
    gw.on('message.delta', (data) => {
      const text = (data as Record<string, string>).text || ''
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'assistant' && last.id === 'streaming') {
          return [...prev.slice(0, -1), { ...last, text: last.text + text }]
        }
        return [...prev, { id: 'streaming', role: 'assistant', text }]
      })
    })

    // Handle message start
    gw.on('message.start', () => {
      setStreaming(true)
    })

    // Handle message complete
    gw.on('message.complete', (data) => {
      setStreaming(false)
      const finalText = (data as Record<string, string>).final_text || ''
      if (finalText) {
        setMessages((prev) => {
          if (prev[prev.length - 1]?.id === 'streaming') {
            return [...prev.slice(0, -1), { id: `msg-${Date.now()}`, role: 'assistant', text: finalText }]
          }
          return prev
        })
      }
    })

    // Handle tool calls
    gw.on('tool.start', (data) => {
      const d = data as Record<string, unknown>
      setMessages((prev) => [
        ...prev,
        { id: `tool-${Date.now()}`, role: 'tool', text: '', toolName: (d.name || d.tool_id) as string },
      ])
    })

    // Handle status updates (thinking, executing)
    gw.on('status.update', (data) => {
      const d = data as Record<string, string>
      if (d.text && d.text !== '工具执行完成' && d.text !== '正在思考...') {
        setMessages((prev) => [
          ...prev,
          { id: `status-${Date.now()}`, role: 'system', text: d.text },
        ])
      }
    })

    // Handle backend errors
    gw.on('backend.exited', () => {
      setConnected(false)
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'system', text: 'Backend disconnected. Please restart the app.' },
      ])
    })

    return () => { try { gw.disconnect() } catch {} }
  }, [])

  const handleSend = useCallback(() => {
    if (!input.trim() || !sessionId || !connected) return

    const userText = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', text: userText }])

    gw.sendPrompt(sessionId, userText)
  }, [input, sessionId, connected])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="app">
      {/* Titlebar */}
      <header className="titlebar">
        <span className="titlebar-text">Bobo</span>
        <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`} />
      </header>

      {/* Chat area */}
      <main className="chat">
        {messages.length === 0 && (
          <div className="welcome">
            <h1>Bobo</h1>
            <p>你的个人 AI 助手</p>
            {isBrowserDev ? (
              <p className="connecting-text">浏览器预览模式（在桌面 App 中可连接后端）</p>
            ) : !connected ? (
              <p className="connecting-text">正在连接...</p>
            ) : null}
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            {msg.role === 'tool' && (
              <div className="tool-badge">
                <span className="tool-icon">🔧</span>
                <span className="tool-name">{msg.toolName || 'Tool'}</span>
              </div>
            )}
            {msg.role === 'system' && (
              <div className="system-msg">{msg.text}</div>
            )}
            {(msg.role === 'user' || msg.role === 'assistant') && (
              <>
                <div className="message-role">{msg.role === 'user' ? 'You' : 'Bobo'}</div>
                <div className="message-text">{msg.text || (streaming && msg.id === 'streaming' ? '...' : '')}</div>
              </>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </main>

      {/* Input area */}
      <footer className="input-area">
        <input
          ref={inputRef}
          className="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isBrowserDev ? '浏览器预览 — 在桌面 App 中可正常使用' : connected ? '输入消息... (Enter 发送)' : '正在连接后端...'}
          disabled={!connected || streaming}
        />
        <button className="send-btn" onClick={handleSend} disabled={!connected || !input.trim()}>
          发送
        </button>
      </footer>
    </div>
  )
}

export default App
