import { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Catalog from './pages/Catalog.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import AddBook from './pages/AddBook.jsx'
import MyLibrary from './pages/MyLibrary.jsx'
import BookDetail from './pages/BookDetail.jsx'
import Librarian from './pages/Librarian.jsx'

export default function App() {
  const { pathname } = useLocation()
  const isChat = pathname === '/librarian'
  useEffect(() => {
    const titles = { '/': 'Library Catalog', '/my-library': 'My Library', '/librarian': 'Library Assistant', '/add': 'Add a Book', '/login': 'Sign In', '/register': 'Create an Account' }
    const title = titles[pathname] || (pathname.endsWith('/edit') ? 'Edit Book' : 'Book Details')
    document.title = `${title} | Library`
  }, [pathname])
  return (
    <div className={`app-shell${isChat ? " chat-shell" : ""}`}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Navbar />
      <main id="main-content">
      <Routes>
        <Route path="/" element={<Catalog />} />
        <Route path="/my-library" element={<ProtectedRoute><MyLibrary /></ProtectedRoute>} />
        <Route path="/book/:id" element={<BookDetail />} />
        <Route path="/book/:id/edit" element={<ProtectedRoute><AddBook /></ProtectedRoute>} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/add"
          element={
            <ProtectedRoute>
              <AddBook />
            </ProtectedRoute>
          }
        />
        <Route
          path="/librarian"
          element={
            <ProtectedRoute>
              <Librarian />
            </ProtectedRoute>
          }
        />
      </Routes>
      </main>
    </div>
  )
}
