import { useMemo } from 'react'
import { Download, Film, Loader2, Play, TriangleAlert, XCircle, Zap } from 'lucide-react'
import type { ProjectStatusResponse, Shot } from '../../types/aiVideos'
import { resolveAssetUrl } from '../../services/aiVideos'

interface GlobalPanelProps {
  shot: Shot | null
  status: ProjectStatusResponse | null
  onGenerateAll: () => void
  onCancelQueue: () => void
  onCompose: () => void
  composeBusy: boolean
  downloadHref: string
}

const PROGRESS_ROWS: Array<{ key: 'image' | 'video' | 'audio'; label: string; bar: string }> = [
  { key: 'image', label: '分镜图', bar: 'bg-success' },
  { key: 'video', label: '视频', bar: 'bg-primary' },
  { key: 'audio', label: '配音', bar: 'bg-success' },
]

export default function GlobalPanel({
  shot,
  status,
  onGenerateAll,
  onCancelQueue,
  onCompose,
  composeBusy,
  downloadHref,
}: GlobalPanelProps) {
  const compose = status?.compose
  const queueActive = (status?.queue.pending ?? 0) + (status?.queue.running ?? 0) > 0
  const canDownload = compose?.state === 'success' && !!compose.video_url
  // final.mp4 的 URL 不随重新合成变化，用状态迁移驱动的时间戳破浏览器缓存
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const composeBuster = useMemo(() => Date.now(), [compose?.state, compose?.stale])

  return (
    <aside className="w-[320px] shrink-0 h-full flex flex-col gap-4 p-5 bg-card border-l border-border overflow-y-auto">
      <span className="text-[13px] font-bold text-text-primary">
        单镜预览{shot ? ` · 镜 ${shot.order}` : ''}
      </span>
      <div className="flex justify-center">
        <div className="relative w-[210px] aspect-[9/16] bg-text-primary rounded-[var(--radius-md)] overflow-hidden flex items-center justify-center">
          {shot?.video.url && shot.video.state === 'success' ? (
            <video
              key={`${shot.id}-${shot.video.version}`}
              src={`${resolveAssetUrl(shot.video.url)}${shot.video.url.includes('?') ? '&' : '?'}v=${shot.video.version}`}
              controls
              className="w-full h-full object-contain"
            >
              <track kind="captions" />
            </video>
          ) : shot?.image.url ? (
            <>
              <img
                src={`${resolveAssetUrl(shot.image.url)}${shot.image.url.includes('?') ? '&' : '?'}v=${shot.image.version}`}
                alt={`镜 ${shot.order} 预览`}
                className="w-full h-full object-cover"
              />
              {shot.dialogue.length > 0 && (
                <span className="absolute bottom-4 left-3 right-3 px-2.5 py-1.5 bg-text-primary/70 rounded-[var(--radius-sm)] text-center text-[11px] font-bold text-white">
                  {shot.dialogue.map((ln) => ln.en).join(' / ')}
                </span>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Play size={22} className="text-white/40" />
              <span className="text-[11px] text-white/40">暂无画面</span>
            </div>
          )}
        </div>
      </div>

      {/* 整体进度 */}
      <div className="flex flex-col gap-3 p-3.5 bg-page rounded-[var(--radius-md)] border border-border">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-text-primary">整体进度</span>
          {queueActive && (
            <button
              onClick={onCancelQueue}
              className="flex items-center gap-1 text-[11px] font-semibold text-text-muted hover:text-error transition-colors cursor-pointer"
            >
              <XCircle size={11} />
              取消排队（{status?.queue.pending ?? 0}）
            </button>
          )}
        </div>
        {PROGRESS_ROWS.map(({ key, label, bar }) => {
          const p = status?.progress[key]
          const done = p?.done ?? 0
          const total = p?.total ?? 0
          return (
            <div key={key} className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-text-muted">{label}</span>
                <span className="text-[11px] font-bold text-text-primary">
                  {done}/{total}
                </span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${bar}`}
                  style={{ width: total > 0 ? `${(done / total) * 100}%` : '0%' }}
                />
              </div>
            </div>
          )
        })}
        {(status?.stale_count ?? 0) > 0 && (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-warning-light rounded-[var(--radius-sm)]">
            <TriangleAlert size={12} className="text-warning shrink-0" />
            <span className="text-[11px] text-warning">有 {status?.stale_count} 项产物已过期</span>
          </div>
        )}
        {status?.queue.paused && status.queue.paused_reason && (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-error-light rounded-[var(--radius-sm)]">
            <TriangleAlert size={12} className="text-error shrink-0" />
            <span className="text-[11px] text-error">{status.queue.paused_reason}</span>
          </div>
        )}
      </div>

      <button
        onClick={onGenerateAll}
        disabled={queueActive}
        className="flex items-center justify-center gap-2 h-11 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {queueActive ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
        {queueActive
          ? `生成中 · 队列 ${(status?.queue.pending ?? 0) + (status?.queue.running ?? 0)}`
          : '批量生成全部'}
      </button>
      <button
        onClick={onCompose}
        disabled={composeBusy || compose?.state === 'running'}
        className="flex items-center justify-center gap-2 h-11 bg-accent hover:bg-accent-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {compose?.state === 'running' || composeBusy ? (
          <Loader2 size={15} className="animate-spin" />
        ) : (
          <Film size={15} />
        )}
        {compose?.state === 'running' ? '合成中…' : compose?.stale ? '重新合成（有更新）' : '合成成片'}
      </button>
      {compose?.state === 'failed' && compose.error && (
        <p className="text-xs text-error -mt-2">合成失败:{compose.error}</p>
      )}
      {canDownload ? (
        <a
          href={downloadHref}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 h-11 bg-card border border-border text-text-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
        >
          <Download size={15} />
          下载 MP4
        </a>
      ) : (
        <span className="flex items-center justify-center gap-2 h-11 bg-page-alt text-text-muted text-sm font-semibold rounded-[var(--radius-sm)] cursor-not-allowed select-none">
          <Download size={15} />
          下载 MP4 · 待合成
        </span>
      )}
      {compose?.state === 'success' && compose.video_url && (
        <video
          src={`${resolveAssetUrl(compose.video_url)}${compose.video_url.includes('?') ? '&' : '?'}v=${composeBuster}`}
          controls
          className="w-full rounded-[var(--radius-md)] border border-border"
        >
          <track kind="captions" />
        </video>
      )}
    </aside>
  )
}
