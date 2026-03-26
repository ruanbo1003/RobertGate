import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Lock, ArrowLeft } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import { resetPassword } from '../services/auth'

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
    if (!/^(?=.*[a-zA-Z])(?=.*\d).{8,32}$/.test(password)) {
      errs.password = '密码需 8-32 字符，包含字母和数字'
    }
    if (password !== confirmPassword) {
      errs.confirmPassword = '两次密码不一致'
    }
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
      <AuthLayout
        heroTitle={"Set New\nPassword."}
        heroSubtitle="Choose a strong password to keep your account secure."
        quote="Security is not a product, but a process."
        quoteAuthor="Bruce Schneier"
      >
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <span className="font-heading text-xs font-semibold text-error tracking-[2px]">
              INVALID
            </span>
            <h2 className="font-heading text-[28px] font-bold text-text-primary">
              Invalid reset link
            </h2>
          </div>
          <p className="font-body text-sm text-text-secondary leading-relaxed">
            This password reset link is invalid or has expired. Please request a
            new one.
          </p>
          <div className="flex flex-col gap-4">
            <Link
              to="/forgot-password"
              className="flex items-center justify-center gap-2 w-full h-[52px] bg-accent hover:bg-accent-hover text-text-on-dark font-heading text-xs font-semibold tracking-[1px] uppercase transition-colors"
            >
              Request New Link
            </Link>
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
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      {success ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <span className="font-heading text-xs font-semibold text-success tracking-[2px]">
              SUCCESS
            </span>
            <h2 className="font-heading text-[28px] font-bold text-text-primary">
              Password updated
            </h2>
          </div>
          <p className="font-body text-sm text-text-secondary leading-relaxed">
            Your password has been reset successfully. Redirecting to login...
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <span className="font-heading text-xs font-semibold text-accent tracking-[2px]">
              NEW PASSWORD
            </span>
            <h2 className="font-heading text-[28px] font-bold text-text-primary">
              Set your new password
            </h2>
            <p className="font-body text-sm text-text-secondary leading-relaxed">
              Your new password must be at least 8 characters and contain both
              letters and numbers.
            </p>
          </div>

          <div className="flex flex-col gap-5">
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
            <p className="text-error text-sm font-body text-center">
              {errors.form}
            </p>
          )}

          <div className="flex flex-col gap-6">
            <Button type="submit" icon={Lock} loading={loading}>
              Reset Password
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
