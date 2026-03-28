import { getPasswordStrength } from '../../utils/validators'

interface PasswordStrengthProps {
  password: string
}

const colorMap = {
  weak: 'bg-error',
  medium: 'bg-warning',
  strong: 'bg-success',
}

const widthMap = {
  weak: 'w-1/3',
  medium: 'w-2/3',
  strong: 'w-full',
}

const textColorMap = {
  weak: 'text-error',
  medium: 'text-warning',
  strong: 'text-success',
}

export default function PasswordStrength({ password }: PasswordStrengthProps) {
  if (!password) return null

  const { strength, label } = getPasswordStrength(password)

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1 bg-border rounded-full overflow-hidden">
        <div
          className={`h-full ${colorMap[strength]} ${widthMap[strength]} rounded-full transition-all duration-200`}
        />
      </div>
      <span className={`font-sans text-xs font-semibold ${textColorMap[strength]}`}>
        {label}
      </span>
    </div>
  )
}
