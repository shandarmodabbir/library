import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client.js'

export default function AddBook() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', author: '', category: '', description: '', isbn: '', publication_year: '', cover_url: '' })
  const [lookup, setLookup] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (id) api.getBook(id).then(book => setForm({ name: book.name, author: book.author, category: book.category, description: book.description, isbn: book.isbn, publication_year: book.publication_year ?? '', cover_url: book.cover_url })).catch(err => setError(err.message))
  }, [id])

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const lookupBook = async () => {
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await api.lookupIsbn(lookup.trim())
      setForm(current => ({ ...current, name: result.name || current.name, author: result.author || current.author, isbn: result.isbn, publication_year: result.publication_year ?? current.publication_year, cover_url: result.cover_url || current.cover_url }))
      setNotice('Details from Open Library. Review the fields and choose a category before saving.')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const body = { ...form, publication_year: form.publication_year ? Number(form.publication_year) : null }
      if (id) await api.updateBook(id, body)
      else await api.createBook(body)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap book-form">
      <div className="card">
        <span className="eyebrow">CATALOG MANAGEMENT</span>
        <h2>{id ? 'Edit book details' : 'Add a book'}</h2>
        {error && <div className="error-banner">{error}</div>}
        <div className="field">
          <label htmlFor="isbn-lookup">ISBN lookup</label>
          <input id="isbn-lookup" placeholder="Enter ISBN or scan with a barcode reader" value={lookup} onChange={e => setLookup(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (!busy && lookup.trim()) lookupBook() } }} />
          <button className="btn secondary" disabled={busy || !lookup.trim()} onClick={lookupBook}>Look up ISBN</button>
          {notice && <p role="status">{notice}</p>}
        </div>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Title</label>
            <input id="name" required value={form.name} onChange={update('name')} />
          </div>
          <div className="field">
            <label htmlFor="author">Author</label>
            <input id="author" required value={form.author} onChange={update('author')} />
          </div>
          <div className="field">
            <label htmlFor="category">Category</label>
            <input id="category" required value={form.category} onChange={update('category')} />
          </div>
          {['description', 'isbn', 'publication_year', 'cover_url'].map(field => (
            <div className="field" key={field}>
              <label htmlFor={field}>{field.replaceAll('_', ' ')} (optional)</label>
              {field === 'description' ? <textarea id={field} maxLength={5000} value={form[field]} onChange={update(field)} /> :
                <input id={field} type={field === 'publication_year' ? 'number' : field === 'cover_url' ? 'url' : 'text'} min={field === 'publication_year' ? 1 : undefined} max={field === 'publication_year' ? 9999 : undefined} value={form[field]} onChange={update(field)} />}
            </div>
          ))}
          <button className="btn" type="submit" disabled={busy} style={{ width: '100%' }}>
            {busy ? 'Saving…' : id ? 'Save changes' : 'Add to Catalog'}
          </button>
        </form>
      </div>
    </div>
  )
}
