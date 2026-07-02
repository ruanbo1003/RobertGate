import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './store/AuthContext'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import NotFoundPage from './pages/NotFoundPage'
import NotImplementedPage from './pages/NotImplementedPage'
import AboutPage from './pages/AboutPage'
import AboutZhPage from './pages/AboutZhPage'
import GalleryPage from './pages/GalleryPage'
import AiToolsLayout from './components/layout/AiToolsLayout'
import TranslatePage from './pages/ai-tools/TranslatePage'
import HanziLibraryPage from './pages/ai-tools/HanziLibraryPage'
import HanziLearnPage from './pages/ai-tools/HanziLearnPage'
import HanziSentencePage from './pages/ai-tools/HanziSentencePage'
import EnglishThemesPage from './pages/ai-tools/EnglishThemesPage'
import EnglishQuizPage from './pages/ai-tools/EnglishQuizPage'
import Text2ImagePage from './pages/ai-tools/Text2ImagePage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/dashboard" element={<NotImplementedPage />} />
          <Route path="/ai-tools" element={<AiToolsLayout />}>
            <Route index element={<Navigate to="/ai-tools/translate" replace />} />
            <Route path="translate" element={<TranslatePage />} />
            <Route path="hanzi/library" element={<HanziLibraryPage />} />
            <Route path="hanzi/learn" element={<HanziLearnPage />} />
            <Route path="hanzi/sentence" element={<HanziSentencePage />} />
            <Route path="english/themes" element={<EnglishThemesPage />} />
            <Route path="english/quiz" element={<EnglishQuizPage />} />
            <Route path="text-to-image" element={<Text2ImagePage />} />
          </Route>
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
