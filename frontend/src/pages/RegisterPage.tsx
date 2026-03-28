import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import Divider from '../components/ui/Divider'
import PasswordStrength from '../components/ui/PasswordStrength'
import { register, checkUsername, checkEmail } from '../services/auth'
import { useAuth } from '../store/AuthContext'
import { useDebouncedCallback } from '../hooks/useDebounce'
import {
  validateUsername,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
} from '../utils/validators'

export default function RegisterPage() {
  const navigate = useNavigate()
  const auth = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [successes, setSuccesses] = useState<Record<string, string>>({})
  const [checking, setChecking] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(false)

  const setFieldError = (field: string, msg: string) =>
    setErrors((prev) => ({ ...prev, [field]: msg }))
  const clearFieldError = (field: string) =>
    setErrors((prev) => ({ ...prev, [field]: '' }))
  const setFieldSuccess = (field: string, msg: string) =>
    setSuccesses((prev) => ({ ...prev, [field]: msg }))
  const clearFieldSuccess = (field: string) =>
    setSuccesses((prev) => ({ ...prev, [field]: '' }))

  const debouncedCheckUsername = useDebouncedCallback(async (value: unknown) => {
    const v = value as string
    if (validateUsername(v)) return
    setChecking((p) => ({ ...p, username: true }))
    const res = await checkUsername(v)
    setChecking((p) => ({ ...p, username: false }))
    if (res.code === 0 && !res.data.available) {
      setFieldError('username', '用户名已被使用')
      clearFieldSuccess('username')
    } else if (res.code === 0) {
      setFieldSuccess('username', '用户名可用')
    }
  }, 500)

  const debouncedCheckEmail = useDebouncedCallback(async (value: unknown) => {
    const v = value as string
    if (validateEmail(v)) return
    setChecking((p) => ({ ...p, email: true }))
    const res = await checkEmail(v)
    setChecking((p) => ({ ...p, email: false }))
    if (res.code === 0 && !res.data.available) {
      setFieldError('email', '邮箱已被注册')
      clearFieldSuccess('email')
    } else if (res.code === 0) {
      setFieldSuccess('email', '邮箱可用')
    }
  }, 500)

  const validate = () => {
    const errs: Record<string, string> = {}
    const u = validateUsername(username)
    if (u) errs.username = u
    const e = validateEmail(email)
    if (e) errs.email = e
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
    const res = await register({ username, email, password })
    setLoading(false)

    if (res.code === 0) {
      auth.login(res.data.access_token, res.data.user)
      navigate('/')
    } else {
      setErrors({ form: res.message })
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
            Create account
          </h2>
          <p className="font-sans text-sm text-muted-foreground">
            Fill in the details to get started
          </p>
        </div>

        <div className="flex flex-col gap-3.5">
          <FormInput
            label="Username"
            placeholder="your_username"
            value={username}
            onChange={(v) => {
              setUsername(v)
              clearFieldError('username')
              clearFieldSuccess('username')
              debouncedCheckUsername(v)
            }}
            error={errors.username}
            success={successes.username}
            loading={checking.username}
          />
          <FormInput
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(v) => {
              setEmail(v)
              clearFieldError('email')
              clearFieldSuccess('email')
              debouncedCheckEmail(v)
            }}
            error={errors.email}
            success={successes.email}
            loading={checking.email}
          />
          <div className="flex flex-col gap-1.5">
            <FormInput
              label="Password"
              type="password"
              placeholder="Min. 8 characters"
              value={password}
              onChange={(v) => {
                setPassword(v)
                clearFieldError('password')
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
              clearFieldError('confirmPassword')
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
          <Button type="submit" icon={UserPlus} loading={loading}>
            Create Account
          </Button>
          <Divider />
          <p className="text-center font-sans text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-primary hover:text-primary-hover transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </form>
    </AuthLayout>
  )
}
