import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import BookCard from '../components/BookCard.jsx'

export default function MyLibrary() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [management, setManagement] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    try {
      const [mine, manage] = await Promise.all([api.myLibrary(), user.role === 'librarian' ? api.manageLibrary() : null])
      setData(mine); setManagement(manage)
    } catch (err) { setError(err.message) }
  }, [user.role])
  useEffect(() => { load() }, [load])
  const perform = async (action) => {
    setBusy(true); setError('')
    try { await action(); await load() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  const returnLoan = async (id) => {
    if (!confirm('Mark this book as returned?')) return
    setBusy(true); setError('')
    try { await api.returnLoan(id); await load() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <div>
    <div className="page-heading"><div><span className="eyebrow">YOUR ACCOUNT</span><h2>My Library</h2><p>Manage your loans, reservations, and reading activity.</p></div><Link className="btn secondary" to="/">Browse catalog →</Link></div>
    {error && <div role="alert" className="error-banner">{error}</div>}
    {!data ? <p>Loading your library…</p> : <>
      <div className="library-summary"><span><strong>{data.contributions.length}</strong>Books contributed</span><span><strong>{data.loans.length}</strong>Currently borrowed</span><span><strong>{data.loans.filter(l => l.overdue).length}</strong>Overdue returns</span></div>
      {(data.loans.some(l => l.due_soon || l.overdue) || data.reservations.some(r => r.ready_until)) && <div className="reminder-banner" role="status">
        {data.loans.filter(l => l.due_soon || l.overdue).map(l => <p key={l.book.id}><Link to={`/book/${l.book.id}`}>{l.book.name}</Link> — {l.overdue ? 'overdue' : 'due within 3 days'}.</p>)}
        {data.reservations.filter(r => r.ready_until).map(r => <p key={r.book.id}><Link to={`/book/${r.book.id}`}>{r.book.name}</Link> is ready to borrow until {new Date(r.ready_until).toLocaleString()}.</p>)}
      </div>}
      <label className="reminder-preference"><input type="checkbox" checked={data.email_reminders} disabled={busy || (!data.email_configured && !data.email_reminders)} onChange={e => perform(() => api.reminders(e.target.checked))} /> Email me return reminders</label>
      {!data.email_configured && <p>Email reminders are available after the library configures email delivery. Due-date reminders appear here automatically.</p>}
      <section className="library-section"><h3>Current loans</h3>
        {!data.loans.length ? <p>No active loans. <Link to="/">Browse the catalog</Link>.</p> : <div className="book-grid">{data.loans.map(loan => <div key={loan.book.id}>
          <p className={loan.overdue ? 'overdue' : ''}>{loan.overdue ? 'Overdue' : 'Due'}: {new Date(loan.due_date).toLocaleDateString()}</p>
          <BookCard book={loan.book} borrowed onChanged={load} />
          <button className="btn secondary" disabled={busy || loan.overdue || loan.renewals >= 2} onClick={() => { if (confirm('Extend this loan by 14 days?')) perform(() => api.renew(loan.book.id)) }}>Renew for 14 days ({loan.renewals}/2 used)</button>
        </div>)}</div>}
      </section>
      <section className="library-section"><h3>Reservations</h3>
        {!data.reservations.length && <p>No reservations. Open an unavailable copy to join its waitlist.</p>}
        {data.reservations.map(r => <div className="management-row" key={r.book.id}><span><Link to={`/book/${r.book.id}`}>{r.book.name}</Link> — {r.ready_until ? 'Ready to borrow' : `Position ${r.position}`}</span><button className="btn secondary" disabled={busy} onClick={() => perform(() => api.cancelReservation(r.book.id))}>Cancel reservation</button></div>)}
      </section>
      <section className="library-section"><h3>Loan history</h3>
        {!data.history.length && <p>Books returned from now on will appear here.</p>}
        {data.history.map(h => <div className="management-row" key={h.id}><span>{h.book_id ? <Link to={`/book/${h.book_id}`}>{h.name}</Link> : h.name} by {h.author}<br />Borrowed {new Date(h.borrowed_at).toLocaleDateString()} · Returned {new Date(h.returned_at).toLocaleDateString()}</span></div>)}
      </section>
      <section className="library-section"><h3>Books you contributed</h3>
        {!data.contributions.length ? <p>You haven’t added a book yet. <Link to="/add">Add one</Link>.</p> : <div className="book-grid">{data.contributions.map(book => <BookCard key={book.id} book={book} borrowed={data.loans.some(l => l.book.id === book.id)} onChanged={load} />)}</div>}
      </section>
      <section className="library-section"><h3>Reading list</h3>
        {!data.reading.length && <p>Open a book to mark it as Want to read, Reading, or Finished.</p>}
        {['want_to_read', 'reading', 'finished'].map(status => <div key={status}><h4>{status.replaceAll('_', ' ')}</h4><ul>{data.reading.filter(r => r.status === status).map(r => <li key={r.book.id}><Link to={`/book/${r.book.id}`}>{r.book.name}</Link></li>)}</ul></div>)}
      </section>
    </>}
    {management && <section className="library-section"><h3>Library administration</h3>
      <h4>All active loans</h4>
      {management.loans.length === 0 && <p>No active loans.</p>}
      {management.loans.map(loan => <div className="management-row" key={loan.book.id}><span><Link to={`/book/${loan.book.id}`}>{loan.book.name}</Link> · {management.members.find(m => m.id === loan.user_id)?.email} · <span className={loan.overdue ? 'overdue' : ''}>Due {new Date(loan.due_date).toLocaleDateString()}</span></span><button className="btn secondary" disabled={busy} onClick={() => returnLoan(loan.book.id)}>Return</button></div>)}
      <h4>Members</h4><ul>{management.members.map(member => <li key={member.id}>{member.email} — {member.role}</li>)}</ul>
    </section>}
  </div>
}
