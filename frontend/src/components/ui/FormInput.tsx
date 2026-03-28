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
    ? 'border-error ring-1 ring-error/20'
    : success
      ? 'border-success ring-1 ring-success/20'
      : 'border-border focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20'

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex justify-between items-center">
        <label
          htmlFor={id}
          className="font-sans text-[13px] font-semibold text-text-secondary"
        >
          {label}
        </label>
        {rightLabel}
      </div>
      <div
        className={`flex items-center w-full h-11 bg-input border px-3.5 rounded-[var(--radius-sm)] transition-all duration-150 ${borderClass}`}
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
          className="flex-1 bg-transparent outline-none font-sans text-base text-text-primary placeholder:text-muted-foreground"
        />
        {loading && (
          <Loader2 size={16} className="ml-2 text-muted-foreground animate-spin" />
        )}
        {!loading && success && (
          <CheckCircle2 size={16} className="ml-2 text-success" />
        )}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            className="ml-2 p-1 text-muted-foreground hover:text-text-secondary transition-colors rounded-[var(--radius-sm)] cursor-pointer"
          >
            {showPassword ? <Eye size={18} /> : <EyeOff size={18} />}
          </button>
        )}
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-error text-xs font-medium">
          {error}
        </p>
      )}
      {!error && success && (
        <p className="text-success text-xs font-medium">{success}</p>
      )}
    </div>
  )
}
