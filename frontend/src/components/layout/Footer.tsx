import { ExternalLink } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="w-full border-t border-border bg-card/50">
      <div className="max-w-6xl mx-auto px-5 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <p className="font-sans text-sm text-muted-foreground">
          © {new Date().getFullYear()} RobertGate
        </p>
        <a
          href="https://github.com/ruanbo1003/RobertGate"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-text-primary transition-colors"
        >
          <ExternalLink size={14} />
          GitHub
        </a>
      </div>
    </footer>
  )
}
