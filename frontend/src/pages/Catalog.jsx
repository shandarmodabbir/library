import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import BookCard from '../components/BookCard.jsx'

const initial = { name: '', author: '', category: '', availability: 'all', sort: 'title', page: 1, page_size: 12 }
export default function Catalog() {
  const { user } = useAuth()
  const [loans, setLoans] = useState([])
  const [result, setResult] = useState({items: [], total: 0})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState(initial)
  const [filters, setFilters] = useState(initial)
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [data, borrowed] = await Promise.all([api.catalog(filters), user ? api.myLoans() : []])
      setResult(data); setLoans(borrowed.map(b => b.id))
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }, [filters, user])
  useEffect(() => { load() }, [load])
  return <div>
    <div className="page-heading catalog-heading"><div><span className="eyebrow">DISCOVER & BORROW</span><h2>Library Catalog</h2><p>Browse titles, check availability, and reserve your next book.</p></div><Link className="btn secondary" to={user ? '/add' : '/register'}>{user ? '+ Add a book' : 'Create an account'}</Link></div>
    <form className="catalog-toolbar" onSubmit={e => { e.preventDefault(); setFilters({...draft, page: 1}) }}>
      {['name','author','category'].map(field => <input key={field} aria-label={field === 'name' ? 'Title' : field} placeholder={field === 'name' ? 'Title' : field} value={draft[field]} onChange={e => setDraft({...draft,[field]:e.target.value})} />)}
      <select aria-label="Availability" value={draft.availability} onChange={e => setDraft({...draft,availability:e.target.value})}><option value="all">All availability</option><option value="available">Available copies</option><option value="unavailable">On loan or reserved</option></select>
      <select aria-label="Sort books" value={draft.sort} onChange={e => setDraft({...draft,sort:e.target.value})}><option value="title">Title A–Z</option><option value="author">Author A–Z</option><option value="newest">Newest first</option></select>
      <button className="btn" disabled={loading}>Search</button>
    </form>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {loading ? <p>Loading catalog…</p> : <>
      <div className="catalog-meta"><span><strong>{result.total}</strong> titles in this collection</span><span>Select a title to view available copies.</span></div>
      {!result.items.length ? <div className="empty-state"><span className="empty-symbol" aria-hidden="true">⌕</span><h3>No matching books</h3><p>No books match these filters. Try another title or broaden your search.</p><button className="btn secondary" onClick={() => { setDraft(initial); setFilters(initial) }}>Clear filters</button></div> : <div className="book-grid">{result.items.map(item => <div className="catalog-item" key={item.title_id}>
        <p className="copy-count">{item.available_copies} of {item.copies} copies available</p>
        <BookCard book={item.book} borrowed={loans.includes(item.book.id)} onChanged={load} />
      </div>)}</div>}
      <div className="pagination"><button className="btn secondary" disabled={filters.page === 1} onClick={() => setFilters(f => ({...f,page:f.page-1}))}>Previous</button><span>Page {filters.page} of {Math.max(1,Math.ceil(result.total / filters.page_size))}</span><button className="btn secondary" disabled={filters.page * filters.page_size >= result.total} onClick={() => setFilters(f => ({...f,page:f.page+1}))}>Next</button></div>
    </>}
  </div>
}
