import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Lock, ArrowLeft } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import PasswordStrength from '../components/ui/PasswordStrength'
import { resetPassword } from '../services/auth'
import { validatePassword, validateConfirmPassword } from '../utils/validators'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const validate = () => {
    const errs: Record<string, string> = {}
    const p = validatePassword(password)
    if (p) errs.password = p
    const c = validateConfirmPassword(password, confirmPassword)
    if (c) errs.confirmPassword = c
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    const res = await resetPassword({ token, password })
    setLoading(false)

    if (res.code === 0) {
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } else {
      setErrors({ form: res.message })
    }
  }

  if (!token) {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
              Invalid reset link
            </h2>
            <p className="font-sans text-sm text-muted-foreground leading-relaxed">
              This link is invalid or has expired. Please request a new one.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Link
              to="/forgot-password"
              className="flex items-center justify-center gap-2 w-full h-11 bg-primary hover:bg-primary-hover text-text-on-primary font-sans text-sm font-semibold rounded-[var(--radius-sm)] transition-colors"
            >
              Request New Link
            </Link>
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
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      {success ? (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
              Password updated
            </h2>
            <p className="font-sans text-sm text-muted-foreground leading-relaxed">
              Your password has been reset. Redirecting to login...
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-7">
          <div className="flex flex-col gap-1">
            <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
              Set new password
            </h2>
            <p className="font-sans text-sm text-muted-foreground leading-relaxed">
              Must be at least 8 characters with letters and numbers.
            </p>
          </div>

          <div className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              <FormInput
                label="New Password"
                type="password"
                placeholder="Min. 8 characters"
                value={password}
                onChange={(v) => {
                  setPassword(v)
                  setErrors((prev) => ({ ...prev, password: '' }))
                }}
                error={errors.password}
              />
              <PasswordStrength password={password} />
            </div>
            <FormInput
              label="Confirm Password"
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(v) => {
                setConfirmPassword(v)
                setErrors((prev) => ({ ...prev, confirmPassword: '' }))
              }}
              error={errors.confirmPassword}
            />
          </div>

          {errors.form && (
            <p className="text-error text-sm font-medium text-center" role="alert">
              {errors.form}
            </p>
          )}

          <div className="flex flex-col gap-5">
            <Button type="submit" icon={Lock} loading={loading}>
              Reset Password
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
