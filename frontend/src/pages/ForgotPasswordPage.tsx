import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import { forgotPassword } from '../services/auth'
import { validateEmail } from '../utils/validators'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const emailErr = validateEmail(email)
    if (emailErr) {
      setError(emailErr)
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
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
              Check your email
            </h2>
            <p className="font-sans text-sm text-muted-foreground leading-relaxed">
              We've sent a password reset link to{' '}
              <span className="font-semibold text-text-primary">{email}</span>.
            </p>
          </div>
          <p className="font-sans text-xs text-muted-foreground">
            Didn't receive the email? Check your spam folder or{' '}
            <button
              onClick={() => setSent(false)}
              className="text-primary hover:text-primary-hover font-semibold transition-colors cursor-pointer"
            >
              try again
            </button>
            .
          </p>
          <div className="flex items-center justify-center gap-1.5 mt-2">
            <ArrowLeft size={14} className="text-muted-foreground" />
            <Link
              to="/login"
              className="font-sans text-sm font-semibold text-primary hover:text-primary-hover transition-colors"
            >
              Back to Sign in
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-7">
          <div className="flex flex-col gap-1">
            <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
              Reset password
            </h2>
            <p className="font-sans text-sm text-muted-foreground leading-relaxed">
              Enter your email and we'll send you a reset link.
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

          <div className="flex flex-col gap-5">
            <Button type="submit" icon={Mail} loading={loading}>
              Send Reset Link
            </Button>
            <div className="flex items-center justify-center gap-1.5">
              <ArrowLeft size={14} className="text-muted-foreground" />
              <Link
                to="/login"
                className="font-sans text-sm font-semibold text-primary hover:text-primary-hover transition-colors"
              >
                Back to Sign in
              </Link>
            </div>
          </div>
        </form>
      )}
    </AuthLayout>
  )
}
