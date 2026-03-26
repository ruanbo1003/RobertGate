import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import Divider from '../components/ui/Divider'
import { login } from '../services/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const res = await login({ email, password })
    setLoading(false)

    if (res.code === 0) {
      localStorage.setItem('token', res.data.access_token)
      navigate('/')
    } else {
      setError(res.message)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <span className="font-heading text-xs font-semibold text-accent tracking-[2px]">
            LOGIN
          </span>
          <h2 className="font-heading text-[28px] font-bold text-text-primary">
            Sign in to your account
          </h2>
        </div>

        <div className="flex flex-col gap-5">
          <FormInput
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={setEmail}
          />
          <FormInput
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={setPassword}
            rightLabel={
              <Link
                to="/forgot-password"
                className="font-body text-[13px] font-medium text-accent hover:text-accent-hover transition-colors"
              >
                Forgot password?
              </Link>
            }
          />
        </div>

        {error && (
          <p className="text-error text-sm font-body text-center">{error}</p>
        )}

        <div className="flex flex-col gap-6">
          <Button type="submit" icon={ArrowRight} loading={loading}>
            Sign In
          </Button>
          <Divider />
          <p className="text-center font-body text-sm text-text-secondary">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-heading font-semibold text-accent hover:text-accent-hover transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </form>
    </AuthLayout>
  )
}
