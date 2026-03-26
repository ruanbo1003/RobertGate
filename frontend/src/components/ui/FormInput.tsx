import { useId, useState } from 'react'
import { Eye, EyeOff, CheckCircle2, Loader2 } from 'lucide-react'

interface FormInputProps {
  label: string
  type?: 'text' | 'email' | 'password'
  placeholder?: string
  value: string
  onChange: (value: string) => void
  onBlur?: () => void
  error?: string
  success?: string
  loading?: boolean
  rightLabel?: React.ReactNode
}

export default function FormInput({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  success,
  loading = false,
  rightLabel,
}: FormInputProps) {
  const id = useId()
  const errorId = `${id}-error`
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && showPassword ? 'text' : type

  const borderClass = error
    ? 'border-error bg-error-light/30'
    : success
      ? 'border-success bg-success-light/30'
      : 'border-border focus-within:border-border-focus'

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex justify-between items-center">
        <label
          htmlFor={id}
          className="font-heading text-[11px] font-semibold text-text-secondary tracking-[1px] uppercase"
        >
          {label}
        </label>
        {rightLabel}
      </div>
      <div
        className={`flex items-center w-full h-12 bg-input-bg border px-4 rounded-[var(--radius-sm)] transition-all duration-200 ${borderClass}`}
      >
        <input
          id={id}
          type={inputType}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          aria-invalid={!!error}
          aria-describedby={error ? errorId : undefined}
          className="flex-1 bg-transparent outline-none font-body text-base text-text-primary placeholder:text-text-muted"
        />
        {loading && (
          <Loader2 size={16} className="ml-2 text-text-muted animate-spin" />
        )}
        {!loading && success && (
          <CheckCircle2 size={16} className="ml-2 text-success" />
        )}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            className="ml-2 p-1 text-text-muted hover:text-text-secondary transition-colors rounded-[var(--radius-sm)]"
          >
            {showPassword ? <Eye size={18} /> : <EyeOff size={18} />}
          </button>
        )}
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-error text-xs font-body">
          {error}
        </p>
      )}
      {!error && success && (
        <p className="text-success text-xs font-body">{success}</p>
      )}
    </div>
  )
}
