import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface FormInputProps {
  label: string
  type?: 'text' | 'email' | 'password'
  placeholder?: string
  value: string
  onChange: (value: string) => void
  error?: string
  rightLabel?: React.ReactNode
}

export default function FormInput({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  rightLabel,
}: FormInputProps) {
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && showPassword ? 'text' : type

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex justify-between items-center">
        <label className="font-heading text-[11px] font-semibold text-text-secondary tracking-[1px] uppercase">
          {label}
        </label>
        {rightLabel}
      </div>
      <div
        className={`flex items-center w-full h-12 bg-input border px-4 transition-colors ${
          error
            ? 'border-error'
            : 'border-border focus-within:border-accent'
        }`}
      >
        <input
          type={inputType}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-transparent outline-none font-body text-[15px] text-text-primary placeholder:text-text-muted"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="ml-2 text-text-muted hover:text-text-secondary transition-colors"
          >
            {showPassword ? <Eye size={18} /> : <EyeOff size={18} />}
          </button>
        )}
      </div>
      {error && (
        <p className="text-error text-xs font-body">{error}</p>
      )}
    </div>
  )
}
