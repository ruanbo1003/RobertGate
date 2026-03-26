import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import Divider from '../components/ui/Divider'
import { register, checkUsername, checkEmail } from '../services/auth'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const validate = () => {
    const errs: Record<string, string> = {}
    if (username.length < 2 || username.length > 20) {
      errs.username = '用户名需要 2-20 个字符'
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = '请输入有效的邮箱地址'
    }
    if (!/^(?=.*[a-zA-Z])(?=.*\d).{8,32}$/.test(password)) {
      errs.password = '密码需 8-32 字符，包含字母和数字'
    }
    if (password !== confirmPassword) {
      errs.confirmPassword = '两次密码不一致'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleBlurUsername = async () => {
    if (username.length >= 2) {
      const res = await checkUsername(username)
      if (res.code === 0 && !res.data.available) {
        setErrors((prev) => ({ ...prev, username: '用户名已被使用' }))
      }
    }
  }

  const handleBlurEmail = async () => {
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      const res = await checkEmail(email)
      if (res.code === 0 && !res.data.available) {
        setErrors((prev) => ({ ...prev, email: '邮箱已被注册' }))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    const res = await register({ username, email, password })
    setLoading(false)

    if (res.code === 0) {
      localStorage.setItem('token', res.data.access_token)
      navigate('/')
    } else {
      setErrors({ form: res.message })
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-7">
        <div className="flex flex-col gap-2">
          <span className="font-heading text-xs font-semibold text-accent tracking-[2px]">
            REGISTER
          </span>
          <h2 className="font-heading text-[28px] font-bold text-text-primary">
            Create your account
          </h2>
        </div>

        <div className="flex flex-col gap-[18px]">
          <div onBlur={handleBlurUsername}>
            <FormInput
              label="Username"
              placeholder="your_username"
              value={username}
              onChange={(v) => {
                setUsername(v)
                setErrors((prev) => ({ ...prev, username: '' }))
              }}
              error={errors.username}
            />
          </div>
          <div onBlur={handleBlurEmail}>
            <FormInput
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(v) => {
                setEmail(v)
                setErrors((prev) => ({ ...prev, email: '' }))
              }}
              error={errors.email}
            />
          </div>
          <FormInput
            label="Password"
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
          <Button type="submit" icon={UserPlus} loading={loading}>
            Create Account
          </Button>
          <Divider />
          <p className="text-center font-body text-sm text-text-secondary">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-heading font-semibold text-accent hover:text-accent-hover transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </form>
    </AuthLayout>
  )
}
