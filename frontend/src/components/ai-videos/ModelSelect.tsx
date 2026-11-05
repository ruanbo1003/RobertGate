import type { ModelInfo } from '../../types/aiVideos'

interface ModelSelectProps {
  value: string
  options: ModelInfo[]
  onChange: (id: string) => void
  label?: string
  compact?: boolean
  disabled?: boolean
}

export default function ModelSelect({
  value,
  options,
  onChange,
  label,
  compact = false,
  disabled = false,
}: ModelSelectProps) {
  const select = (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-label={label ?? '选择模型'}
      className={`${compact ? 'h-8 text-xs max-w-[200px]' : 'h-10 text-sm w-full'} px-2.5 bg-card border border-border rounded-[var(--radius-sm)] text-text-primary cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
    >
      {options.map((m) => (
        <option key={m.id} value={m.id}>
          {m.name}
        </option>
      ))}
    </select>
  )

  if (!label) return select
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[13px] font-semibold text-text-primary">{label}</label>
      {select}
    </div>
  )
}
