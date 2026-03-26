import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import { forgotPassword } from '../services/auth'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('请输入有效的邮箱地址')
      return
    }

    setError('')
    setLoading(true)
    const res = await forgotPassword({ email })
    setLoading(false)

    if (res.code === 0) {
      setSent(true)
    } else {
      setError(res.message)
    }
  }

  return (
    <AuthLayout>
      {sent ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <span className="font-heading text-xs font-semibold text-success tracking-[2px]">
              SENT
            </span>
            <h2 className="font-heading text-[28px] font-bold text-text-primary">
              Check your email
            </h2>
          </div>
          <p className="font-body text-sm text-text-secondary leading-relaxed">
            We've sent a password reset link to{' '}
            <span className="font-semibold text-text-primary">{email}</span>.
            Please check your inbox and follow the instructions.
          </p>
          <p className="font-body text-xs text-text-muted">
            Didn't receive the email? Check your spam folder or{' '}
            <button
              onClick={() => setSent(false)}
              className="text-accent hover:text-accent-hover font-semibold transition-colors"
            >
              try again
            </button>
            .
          </p>
          <div className="flex items-center justify-center gap-1.5 mt-2">
            <ArrowLeft size={14} className="text-text-secondary" />
            <span className="font-body text-sm text-text-secondary">
              Back to{' '}
            </span>
            <Link
              to="/login"
              className="font-heading text-sm font-semibold text-accent hover:text-accent-hover transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <span className="font-heading text-xs font-semibold text-accent tracking-[2px]">
              RESET
            </span>
            <h2 className="font-heading text-[28px] font-bold text-text-primary">
              Reset your password
            </h2>
            <p className="font-body text-sm text-text-secondary leading-relaxed">
              Enter the email address associated with your account and we'll
              send you a link to reset your password.
            </p>
          </div>

          <FormInput
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(v) => {
              setEmail(v)
              setError('')
            }}
            error={error}
          />

          <div className="flex flex-col gap-6">
            <Button type="submit" icon={Mail} loading={loading}>
              Send Reset Link
            </Button>
            <div className="flex items-center justify-center gap-1.5">
              <ArrowLeft size={14} className="text-text-secondary" />
              <span className="font-body text-sm text-text-secondary">
                Back to{' '}
              </span>
              <Link
                to="/login"
                className="font-heading text-sm font-semibold text-accent hover:text-accent-hover transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </form>
      )}
    </AuthLayout>
  )
}
