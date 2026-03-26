export default function Divider({ text = 'OR' }: { text?: string }) {
  return (
    <div className="flex items-center gap-4 w-full">
      <div className="flex-1 h-px bg-border" />
      <span className="font-heading text-[10px] font-semibold text-text-muted tracking-[1px]">
        {text}
      </span>
      <div className="flex-1 h-px bg-border" />
    </div>
  )
}
