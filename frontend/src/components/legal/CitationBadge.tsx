import { BookOpen } from 'lucide-react'
import type { Citation } from '../../types/legalConsult'

interface CitationBadgeProps {
  citation: Citation
  onClick: (citation: Citation) => void
}

export default function CitationBadge({ citation, onClick }: CitationBadgeProps) {
  return (
    <button
      onClick={() => onClick(citation)}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-primary-light text-primary text-xs font-semibold transition-colors duration-150 hover:bg-primary hover:text-text-on-primary cursor-pointer"
      aria-label={`查看条文：${citation.label}`}
      title={`查看《民法典》${citation.label}原文`}
    >
      <BookOpen size={12} />
      {citation.label}
    </button>
  )
}
