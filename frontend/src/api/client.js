const TOKEN_KEY = 'reading_room_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request(path, { method = 'GET', body, form, auth = false } = {}) {
  const headers = {}
  let payload = body

  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(body).toString()
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${import.meta.env.VITE_API_URL || ""}${path}`, { method, headers, body: payload })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* no json body */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (res.status === 204) return null
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  register: (email, password) => request('/users/', { method: 'POST', body: { email, password } }),

  login: (email, password) =>
    request('/login/', { method: 'POST', form: true, body: { username: email, password } }),

  getUser: (id) => request(`/users/${id}`, { auth: true }),

  searchBooks: ({ name = '', author = '', category = '' } = {}) => {
    const params = new URLSearchParams()
    if (name) params.set('name', name)
    if (author) params.set('author', author)
    if (category) params.set('category', category)
    const qs = params.toString()
    return request(`/books/${qs ? `?${qs}` : ''}`)
  },

  catalog: (filters = {}) => request(`/books/catalog?${new URLSearchParams(Object.entries(filters).filter(([,v]) => v !== '' && v != null))}`),
  copies: (id) => request(`/books/${id}/copies`),
  lookupIsbn: (isbn) => request(`/books/isbn/${encodeURIComponent(isbn)}`, { auth: true }),
  renew: (id) => request(`/borrow/${id}/renew`, { method: 'POST', auth: true }),
  reserve: (id) => request(`/borrow/${id}/reserve`, { method: 'POST', auth: true }),
  cancelReservation: (id) => request(`/borrow/${id}/reserve`, { method: 'DELETE', auth: true }),
  reminders: (enabled) => request('/library/reminders', { method: 'PUT', body: { enabled }, auth: true }),

  getBook: (id) => request(`/books/${id}`),

  createBook: (book) => request('/books/', { method: 'POST', body: book, auth: true }),

  updateBook: (id, book) => request(`/books/${id}`, { method: 'PUT', body: book, auth: true }),

  deleteBook: (id) => request(`/books/${id}`, { method: 'DELETE', auth: true }),

  myLibrary: () => request('/library/mine', { auth: true }),
  manageLibrary: () => request('/library/manage', { auth: true }),
  returnLoan: (id) => request(`/library/loans/${id}`, { method: 'DELETE', auth: true }),
  readingStatus: (id, status) => request(`/library/reading/${id}`, { method: 'PUT', body: { status }, auth: true }),
  renameChat: (id, title) => request(`/agent/sessions/${encodeURIComponent(id)}`, { method: 'PATCH', body: { title }, auth: true }),
  deleteChat: (id) => request(`/agent/sessions/${encodeURIComponent(id)}`, { method: 'DELETE', auth: true }),

  myLoans: () => request("/borrow/mine", { auth: true }),

  setBorrow: (bookId, dir) => request('/borrow/', { method: 'POST', body: { book_id: bookId, dir }, auth: true }),

  chatSessions: () => request('/agent/sessions', { auth: true }),

  chatSession: (id) => request(`/agent/sessions/${encodeURIComponent(id)}`, { auth: true }),

  askLibrarian: (message, sessionId, requestId) => request('/agent/chat', { method: 'POST', body: { message, session_id: sessionId, request_id: requestId }, auth: true })
}
