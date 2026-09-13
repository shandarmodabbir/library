import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'

const welcome = [{ role: 'assistant', content: "I’m your Library assistant. I can help you search the catalog, check your loans, and add books." }]

export default function Librarian() {
  const [renamingId, setRenamingId] = useState(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [renameError, setRenameError] = useState('')
  const [historyOpen, setHistoryOpen] = useState(false)
  const [messages, setMessages] = useState(welcome)
  const [query, setQuery] = useState('')
  const [failed, setFailed] = useState(false)
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pendingRequest = useRef(null)
  const logRef = useRef(null)

  useEffect(() => {
    let active = true
    api.chatSessions().then(data => { if (active) setSessions(data) })
      .catch(err => { if (active) setError(err.message) })
      .finally(() => { if (active) setHistoryLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const startRename = (session) => {
    setRenamingId(session.id)
    setRenameTitle(session.title)
    setRenameError('')
  }
  const renameChat = async (event, id) => {
    event.preventDefault()
    const title = renameTitle.trim()
    if (!title || busy) return
    setBusy(true)
    setRenameError('')
    try {
      const saved = await api.renameChat(id, title)
      setSessions(items => items.map(session => session.id === id ? { ...session, title: saved.title } : session))
      setQuery('')
      setRenamingId(null)
    } catch (err) { setRenameError(err.message) }
    finally { setBusy(false) }
  }
  const deleteChat = async (id) => {
    if (!confirm('Permanently delete this conversation?')) return
    setBusy(true)
    try {
      await api.deleteChat(id)
      setSessions(items => items.filter(s => s.id !== id))
      if (id === sessionId) newChat()
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const openSession = async (id) => {
    setBusy(true)
    setError('')
    try {
      const session = await api.chatSession(id)
      setHistoryOpen(false)
      setSessionId(session.id)
      setMessages(session.messages.length ? session.messages : welcome)
      setInput('')
      setFailed(false)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const newChat = () => {
    setFailed(false)
    pendingRequest.current = null
    setSessionId(null)
    setHistoryOpen(false)
    setMessages(welcome)
    setInput('')
    setError('')
  }

  const send = async (e) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setFailed(false)
    if (!pendingRequest.current || pendingRequest.current.message !== text || pendingRequest.current.sessionId !== sessionId) {
      pendingRequest.current = { id: crypto.randomUUID(), message: text, sessionId }
    }
    const previous = messages
    setMessages(m => [...m, { role: 'user', content: text }])
    setInput('')
    setBusy(true)
    setError('')
    try {
      const result = await api.askLibrarian(text, sessionId, pendingRequest.current.id)
      pendingRequest.current = null
      setSessionId(result.session_id)
      setMessages(m => [...m, { role: 'assistant', content: result.response + (result.actions?.length ? '\n\nConfirmed actions:\n' + result.actions.join('\n') : '') }])
      try { setSessions(await api.chatSessions()) }
      catch { setError('Reply saved, but history could not refresh. Reload to try again.') }
    } catch (err) {
      setFailed(true)
      setMessages(previous)
      setInput(text)
      setError(err.message)
    } finally { setBusy(false) }
  }

  return (
    <div className="librarian-page">
      <div className="chat-heading"><h2>Library Assistant</h2><button className="btn secondary history-toggle" aria-expanded={historyOpen} aria-controls="chat-history" onClick={() => setHistoryOpen(open => !open)}>{historyOpen ? "Hide history" : "Chat history"}</button></div>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <div className={`librarian-layout${historyOpen ? " history-open" : ""}`}>
        <aside id="chat-history" className="chat-history" aria-label="Chat history">
          <button className="btn" onClick={newChat} disabled={busy}>+ New chat</button>
          <h3>Previous conversations</h3>
          <input className="history-search" aria-label="Search conversations" placeholder="Search titles…" value={query} onChange={e => setQuery(e.target.value)} />
          {historyLoading ? <p>Loading history…</p> : sessions.length === 0 ? <p>Your conversations will appear here after your first message.</p> : (
            <ul className="session-list">
              {!sessions.some(s => s.title.toLowerCase().includes(query.toLowerCase())) && <li>No conversations match.</li>}
              {sessions.filter(s => s.title.toLowerCase().includes(query.toLowerCase())).map(session => (
                <li key={session.id}>
                  {renamingId === session.id ? <form className="session-rename" onSubmit={event => renameChat(event, session.id)}>
                    <label htmlFor="conversation-title">Conversation title</label>
                    <input id="conversation-title" autoFocus value={renameTitle} maxLength={80} disabled={busy}
                      onFocus={event => event.target.select()} onChange={event => setRenameTitle(event.target.value)}
                      onKeyDown={event => { if (event.key === 'Escape' && !busy) setRenamingId(null) }} />
                    <div className="session-rename-actions"><button className="btn" disabled={busy || !renameTitle.trim()} type="submit">{busy ? 'Saving…' : 'Save'}</button><button className="btn secondary" disabled={busy} type="button" onClick={() => setRenamingId(null)}>Cancel</button></div>
                    {renameError && <p role="alert" className="rename-error">{renameError}</p>}
                  </form> : <>
                  <button className={`session-button ${sessionId === session.id ? 'selected' : ''}`}
                    aria-current={sessionId === session.id ? 'true' : undefined}
                    disabled={busy} onClick={() => openSession(session.id)}>
                    <span>{session.title}</span>
                    {session.updated_at && <time dateTime={new Date(session.updated_at * 1000).toISOString()}>{new Date(session.updated_at * 1000).toLocaleDateString()}</time>}
                  </button>
                  <div className="session-actions"><button disabled={busy} onClick={() => startRename(session)}>Rename</button><button disabled={busy} onClick={() => deleteChat(session.id)}>Delete</button></div>
                  </>}
                </li>
              ))}
            </ul>
          )}
        </aside>
        <div className="chat-wrap" aria-busy={busy}>
          <div className="chat-log" ref={logRef} role="log" aria-label="Conversation">
            {messages === welcome && <div className="chat-welcome"><span className="welcome-mark" aria-hidden="true">✳</span><h3>How can I help you?</h3><p>Search the catalog, manage your loans, or get help adding a book.</p><div className="suggestion-list">{['Find me a novel', 'What have I borrowed?', 'Help me add a book'].map(text => <button key={text} disabled={busy} onClick={() => { setInput(text); document.getElementById('chat-message')?.focus() }}>{text} ↗</button>)}</div></div>}
            {messages !== welcome && messages.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role}`}>
                <span className="role-label">{m.role === 'user' ? 'You' : 'Library Assistant'}</span>
                <ChatContent content={m.content} />
              </div>
            ))}
            {busy && <div className="chat-msg assistant"><span className="typing-dots">Please wait</span></div>}
          </div>
          <form className="chat-input-row" onSubmit={send}>
            <input id="chat-message" aria-label="Message to the librarian" placeholder="e.g. find me a historical novel about Rome"
              value={input} onChange={e => setInput(e.target.value)} disabled={busy} maxLength={10000} />
            {failed && <button className="btn secondary" type="button" disabled={busy || !input.trim()} onClick={() => send()}>Retry</button>}
            <button className="btn" type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      </div>
    </div>
  )
}


function ChatContent({ content }) {
  const parts = content.split(/(\[[^\]]+\]\(\/book\/\d+\))/g)
  return parts.map((part, index) => {
    const match = part.match(/^\[([^\]]+)\]\((\/book\/\d+)\)$/)
    return match ? <Link key={index} className="chat-book-link" to={match[2]}><span className="eyebrow">Open book</span>{match[1]} →</Link> : part
  })
}
