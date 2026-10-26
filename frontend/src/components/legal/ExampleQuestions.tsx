import { MessageCircle, Scale } from 'lucide-react'

interface ExampleQuestionsProps {
  onSelect: (question: string) => void
  disabled: boolean
}

const EXAMPLES = [
  '租房押金不退怎么办？',
  '借出去的钱要不回来怎么办？',
  '离婚后夫妻财产如何分割？',
  '网购商品有质量问题如何维权？',
]

export default function ExampleQuestions({ onSelect, disabled }: ExampleQuestionsProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 h-full py-10">
      <div className="w-[72px] h-[72px] rounded-full bg-primary-light flex items-center justify-center">
        <Scale size={32} className="text-primary" />
      </div>
      <h2 className="text-2xl font-bold tracking-tight text-text-primary mt-2">法律咨询助手</h2>
      <p className="text-sm text-text-muted text-center max-w-md">
        基于《中华人民共和国民法典》解读你的法律问题，支持多轮追问，引用条文均可查证
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5 w-full max-w-2xl">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            disabled={disabled}
            className="flex items-center gap-2.5 px-4 py-4 bg-card border border-border rounded-[var(--radius-md)] text-sm text-text-primary text-left transition-all duration-150 hover:border-border-focus hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <MessageCircle size={16} className="text-primary shrink-0" />
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
