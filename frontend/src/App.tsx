import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './store/AuthContext'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import NotFoundPage from './pages/NotFoundPage'
import NotImplementedPage from './pages/NotImplementedPage'
import ForbiddenPage from './pages/ForbiddenPage'
import AboutPage from './pages/AboutPage'
import AboutZhPage from './pages/AboutZhPage'
import GalleryPage from './pages/GalleryPage'
import AiToolsLayout from './components/layout/AiToolsLayout'
import ProtectedRoute from './components/layout/ProtectedRoute'
import TranslatePage from './pages/ai-tools/TranslatePage'
import HanziLevelListPage from './pages/ai-tools/HanziLevelListPage'
import HanziCharacterGridPage from './pages/ai-tools/HanziCharacterGridPage'
import EnglishThemesPage from './pages/ai-tools/EnglishThemesPage'
import EnglishQuizPage from './pages/ai-tools/EnglishQuizPage'
import Text2ImagePage from './pages/ai-tools/Text2ImagePage'
import AdminLevelListPage from './pages/admin/AdminLevelListPage'
import AdminCharacterListPage from './pages/admin/AdminCharacterListPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/ai-tools"
            element={
              <ProtectedRoute>
                <AiToolsLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/ai-tools/translate" replace />} />
            <Route path="translate" element={<TranslatePage />} />
            <Route path="hanzi" element={<HanziLevelListPage />} />
            <Route path="hanzi/levels/:levelId" element={<HanziCharacterGridPage />} />
            <Route path="admin/hanzi" element={<AdminLevelListPage />} />
            <Route
              path="admin/hanzi/levels/:levelId/characters"
              element={<AdminCharacterListPage />}
            />
            <Route path="english/themes" element={<EnglishThemesPage />} />
            <Route path="english/quiz" element={<EnglishQuizPage />} />
            <Route path="text-to-image" element={<Text2ImagePage />} />
          </Route>
          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="/bookmarks" element={<NotImplementedPage />} />
          <Route path="/gallery" element={<GalleryPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/about/zh" element={<AboutZhPage />} />
          <Route path="/not-implemented" element={<NotImplementedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
