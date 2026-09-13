import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import BookCard from '../components/BookCard.jsx'

export default function BookDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [book, setBook] = useState(null)
  const [copies, setCopies] = useState([])
  const [reservation, setReservation] = useState(null)
  const [borrowed, setBorrowed] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    try {
      const [item, mine, allCopies] = await Promise.all([api.getBook(id), user ? api.myLibrary() : null, api.copies(id)])
      setCopies(allCopies)
      setReservation(mine?.reservations.find(r => r.book.id === item.id) || null)
      setBook(item); setBorrowed(mine?.loans.some(l => l.book.id === item.id) || false)
      setStatus(mine?.reading.find(r => r.book.id === item.id)?.status || '')
    } catch (err) { setError(err.message) }
  }, [id, user])
  useEffect(() => { load() }, [load])
  const update = async (value) => {
    setBusy(true); setError('')
    try { await api.readingStatus(id, value || null); setStatus(value) }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  const reserve = async () => {
    setBusy(true); setError('')
    try {
      if (reservation) await api.cancelReservation(id)
      else await api.reserve(id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  const claim = async () => {
    if (!confirm('Borrow your reserved copy for 14 days?')) return
    setBusy(true)
    try { await api.setBorrow(id, 1); await load() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <div>
    <Link to="/">← Catalog</Link>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {book && <div className="book-detail">
      <BookCard book={book} borrowed={borrowed} onChanged={load} onDeleted={() => navigate("/")} />
      <div className="card"><h2>{book.name}</h2><p>{book.description || 'No description yet.'}</p>
        {book.isbn && <p>ISBN: {book.isbn}</p>}{book.publication_year && <p>Published: {book.publication_year}</p>}
        {user && !borrowed && (!book.available || reservation) && <div className="reservation-box">
          {reservation ? <p>{reservation.ready_until ? `Ready for you until ${new Date(reservation.ready_until).toLocaleString()}` : `Your queue position: ${reservation.position}`}</p> : <p>Join this copy’s first-come-first-served waitlist.</p>}
          {reservation?.ready_until && <button className="btn" disabled={busy} onClick={claim}>Borrow reserved copy</button>}
          <button className="btn secondary" disabled={busy} onClick={reserve}>{reservation ? 'Cancel reservation' : 'Reserve this copy'}</button>
        </div>}
        <h3>Available copies and status</h3>
        <ul>{copies.map(copy => <li key={copy.id}><Link to={`/book/${copy.id}`}>Copy #{copy.id}</Link> — {copy.available ? 'Available' : 'On loan or reserved'}</li>)}</ul>
        {user && <div className="field"><label htmlFor="reading-status">Your reading status</label><select id="reading-status" value={status} disabled={busy} onChange={e => update(e.target.value)}>
          <option value="">Not on reading list</option><option value="want_to_read">Want to read</option><option value="reading">Reading</option><option value="finished">Finished</option>
        </select></div>}
        {user && (user.id === book.provider_user_id || user.role === 'librarian') && <Link className="btn secondary" to={`/book/${book.id}/edit`}>Edit details</Link>}
      </div>
    </div>}
  </div>
}
