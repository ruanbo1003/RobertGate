export default function Divider({ text = 'OR' }: { text?: string }) {
  return (
    <div className="flex items-center gap-3 w-full">
      <div className="flex-1 h-px bg-border" />
      <span className="font-sans text-xs font-medium text-muted-foreground">
        {text}
      </span>
      <div className="flex-1 h-px bg-border" />
    </div>
  )
}
