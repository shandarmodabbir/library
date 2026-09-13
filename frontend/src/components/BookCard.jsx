import { Link } from 'react-router-dom'
import { useState } from 'react'
import { api } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function BookCard({ book, borrowed, onChanged, onDeleted }) {
  const { user } = useAuth()
  const [coverFailed, setCoverFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  const isOwner = user && (book.provider_user_id === user.id || user.role === "librarian")

  const toggleBorrow = async () => {
    if (!confirm(borrowed ? `Return "${book.name}"?` : `Borrow "${book.name}" for 14 days?`)) return
    setBusy(true)
    try {
      await api.setBorrow(book.id, borrowed ? 0 : 1)
      await onChanged?.()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Remove "${book.name}" from the catalog?`)) return
    setBusy(true)
    try {
      await api.deleteBook(book.id)
      if (onDeleted) onDeleted()
      else onChanged?.()
    } catch (err) {
      alert(err.message)
      setBusy(false)
    }
  }

  return (
    <article className="book-card">
      <Link to={`/book/${book.id}`} className={`book-art tone-${book.id % 4}`} tabIndex={-1} aria-hidden="true">
        {book.cover_url && !coverFailed ? <img src={book.cover_url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setCoverFailed(true)} /> : <div className="cover-lettering"><span className="cover-edition">LIBRARY</span><span className="cover-title">{book.name}</span><span className="cover-rule" /><span className="cover-author">{book.author}</span></div>}
      </Link>
      <div className="book-card-body">
      <span className={`stamp ${book.available ? 'available' : ''}`}>
        {borrowed ? 'Borrowed by you' : book.available ? 'Available' : 'Unavailable'}
      </span>
      <Link className="book-name" to={`/book/${book.id}`}>{book.name}</Link>
      <div className="book-author">by {book.author}</div>
      <span className="book-category">{book.category}</span>


      <div className="book-actions">
        {user && (
          <button className="btn secondary" disabled={busy || (!borrowed && !book.available)} onClick={toggleBorrow}>
            {borrowed ? 'Return' : book.available ? 'Borrow' : 'Unavailable'}
          </button>
        )}
        {isOwner && (
          <button className="btn danger" disabled={busy} onClick={handleDelete}>
            Remove
          </button>
        )}
      </div>
      </div>
    </article>
  )
}
