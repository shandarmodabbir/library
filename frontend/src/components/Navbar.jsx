import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const navClass = ({ isActive }) => `nav-link${isActive ? ' active' : ''}`
  return <header className="drawer-nav">
    <Link to="/" className="brand" aria-label="Library home">
      <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 4c4-1 7 0 9 2 2-2 5-3 9-2v15c-4-1-7 0-9 2-2-2-5-3-9-2V4Z"/><path d="M12 6v15"/></svg></span>
      <span className="brand-title">Library<span className="brand-subtitle">Library management, simplified</span></span>
    </Link>
    <nav className="nav-links" aria-label="Main navigation">
      <NavLink to="/" end className={navClass}>Catalog</NavLink>
      {user && <><NavLink to="/my-library" className={navClass}>My Library</NavLink><NavLink to="/librarian" className={navClass}>Library Assistant</NavLink><NavLink to="/add" className={navClass}>Add Book</NavLink></>}
    </nav>
    {user ? <details className="account-menu"><summary aria-label="Account menu"><span className="avatar">{user.email[0].toUpperCase()}</span><span className="account-label">My account</span><span aria-hidden="true">⌄</span></summary><div className="account-popover"><span className="eyebrow">Signed in as</span><p>{user.email}</p><button className="btn secondary" onClick={() => { logout(); navigate('/login') }}>Sign out</button></div></details> : <NavLink to="/login" className="btn">Sign In</NavLink>}
  </header>
}
