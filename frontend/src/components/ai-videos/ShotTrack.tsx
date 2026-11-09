import { ArrowDown, ArrowUp, Clapperboard, ImageIcon, Plus, Volume2 } from 'lucide-react'
import type { Shot } from '../../types/aiVideos'
import { resolveAssetUrl } from '../../services/aiVideos'
import StatusDot from './StatusDot'

interface ShotTrackProps {
  shots: Shot[]
  selectedId: number | null
  onSelect: (id: number) => void
  onAdd: () => void
  onMove: (id: number, dir: -1 | 1) => void
}

export default function ShotTrack({ shots, selectedId, onSelect, onAdd, onMove }: ShotTrackProps) {
  return (
    <aside className="w-[280px] shrink-0 h-full flex flex-col bg-card border-r border-border">
      <div className="flex items-center justify-between px-4 py-3.5 shrink-0">
        <span className="text-[13px] font-bold text-text-primary">分镜 · {shots.length}</span>
        <button
          onClick={onAdd}
          aria-label="新增分镜"
          className="w-8 h-8 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-primary hover:bg-primary-light/50 transition-colors cursor-pointer"
        >
          <Plus size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-3 flex flex-col gap-2">
        {shots.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <Clapperboard size={22} className="text-text-muted/40" />
            <p className="text-xs text-text-muted px-4">还没有分镜，在「剧本」里拆分镜，或点右上角 + 手动添加</p>
          </div>
        )}
        {shots.map((shot, idx) => {
          const selected = shot.id === selectedId
          return (
            <div
              key={shot.id}
              onClick={() => onSelect(shot.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onSelect(shot.id)}
              className={`group relative flex items-center gap-2.5 p-2.5 rounded-[var(--radius-md)] border cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 ${
                selected
                  ? 'border-primary bg-primary-light/50'
                  : 'border-border bg-card hover:border-primary/40'
              }`}
            >
              <div className="w-11 h-[66px] shrink-0 rounded-md bg-page-alt overflow-hidden">
                {shot.image.url && (
                  <img
                    src={`${resolveAssetUrl(shot.image.url)}${shot.image.url.includes('?') ? '&' : '?'}v=${shot.image.version}`}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text-primary">镜 {shot.order}</span>
                  <span className="text-[11px] text-text-muted">
                    {shot.duration_estimate.toFixed(1)}s
                  </span>
                </div>
                <p className="text-[11px] text-text-muted truncate">
                  {shot.dialogue.map((ln) => ln.en).join(' / ') || '（空台词）'}
                </p>
                <div className="flex items-center gap-2.5">
                  <span className="flex items-center gap-1" title="分镜图">
                    <ImageIcon size={11} className="text-text-muted" />
                    <StatusDot state={shot.image.state} stale={shot.image.stale} />
                  </span>
                  <span className="flex items-center gap-1" title="视频">
                    <Clapperboard size={11} className="text-text-muted" />
                    <StatusDot state={shot.video.state} stale={shot.video.stale} />
                  </span>
                  {shot.audio && (
                    <span className="flex items-center gap-1" title="配音">
                      <Volume2 size={11} className="text-text-muted" />
                      <StatusDot state={shot.audio.state} stale={shot.audio.stale} />
                    </span>
                  )}
                  {shot.dialogue.length >= 2 && (
                    <span className="ml-auto px-1.5 py-0.5 bg-primary-light/60 rounded-full text-[10px] font-semibold text-primary">
                      {shot.dialogue.length}人
                    </span>
                  )}
                </div>
              </div>
              <div className="absolute right-1.5 top-1.5 flex-col gap-0.5 hidden group-hover:flex">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onMove(shot.id, -1)
                  }}
                  disabled={idx === 0}
                  aria-label="上移分镜"
                  className="w-6 h-6 flex items-center justify-center bg-card border border-border rounded text-text-muted hover:text-primary disabled:opacity-30 transition-colors cursor-pointer"
                >
                  <ArrowUp size={11} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onMove(shot.id, 1)
                  }}
                  disabled={idx === shots.length - 1}
                  aria-label="下移分镜"
                  className="w-6 h-6 flex items-center justify-center bg-card border border-border rounded text-text-muted hover:text-primary disabled:opacity-30 transition-colors cursor-pointer"
                >
                  <ArrowDown size={11} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
