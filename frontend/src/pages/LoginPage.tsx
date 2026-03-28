import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import AuthLayout from '../components/layout/AuthLayout'
import FormInput from '../components/ui/FormInput'
import Button from '../components/ui/Button'
import Divider from '../components/ui/Divider'
import { login } from '../services/auth'
import { useAuth } from '../store/AuthContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const auth = useAuth()
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
      auth.login(res.data.access_token, res.data.user)
      navigate('/')
    } else {
      setError(res.message)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-7">
        <div className="flex flex-col gap-1">
          <h2 className="font-sans text-2xl font-bold text-text-primary tracking-tight">
            Sign in
          </h2>
          <p className="font-sans text-sm text-muted-foreground">
            Enter your credentials to access your account
          </p>
        </div>

        <div className="flex flex-col gap-4">
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
                className="font-sans text-[13px] font-medium text-primary hover:text-primary-hover transition-colors"
              >
                Forgot password?
              </Link>
            }
          />
        </div>

        {error && (
          <p className="text-error text-sm font-medium text-center" role="alert">{error}</p>
        )}

        <div className="flex flex-col gap-5">
          <Button type="submit" icon={ArrowRight} loading={loading}>
            Sign In
          </Button>
          <Divider />
          <p className="text-center font-sans text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-semibold text-primary hover:text-primary-hover transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </form>
    </AuthLayout>
  )
}
