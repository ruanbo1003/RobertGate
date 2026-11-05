import Modal from '../ui/Modal'

interface ConfirmDialogProps {
  open: boolean
  title: string
  children: React.ReactNode
  confirmText?: string
  danger?: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open,
  title,
  children,
  confirmText = '确认',
  danger = false,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      width={420}
      footer={
        <>
          <button
            onClick={onCancel}
            className="h-10 px-4 text-sm font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`h-10 px-4 text-sm font-semibold text-white rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
              danger ? 'bg-error hover:bg-error/90' : 'bg-primary hover:bg-primary-hover'
            }`}
          >
            {loading && (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {confirmText}
          </button>
        </>
      }
    >
      <div className="text-sm text-text-secondary leading-relaxed">{children}</div>
    </Modal>
  )
}
