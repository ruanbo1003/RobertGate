import { Pencil, Trash2, UserRound } from 'lucide-react'
import type { Character } from '../../types/aiVideos'
import { resolveAssetUrl } from '../../services/aiVideos'

interface CharacterCardProps {
  character: Character
  onEdit: () => void
  onDelete: () => void
}

export default function CharacterCard({ character, onEdit, onDelete }: CharacterCardProps) {
  return (
    <div className="group flex flex-col bg-card rounded-[var(--radius-lg)] border border-border hover:border-primary/30 shadow-sm hover:shadow-md transition-all duration-150 hover:-translate-y-0.5 overflow-hidden">
      <div className="relative w-full aspect-[9/16] bg-page-alt overflow-hidden">
        {character.cover_image_url ? (
          <img
            src={resolveAssetUrl(character.cover_image_url)}
            alt={`${character.name} 设定图`}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <UserRound size={32} className="text-text-muted/40" />
          </div>
        )}
        <span className="absolute top-3 left-3 px-2.5 py-1 bg-card rounded-full shadow-sm text-[11px] font-semibold text-text-primary">
          已用于 {character.used_count} 集
        </span>
        <div className="absolute top-3 right-3 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            aria-label={`编辑 ${character.name}`}
            className="w-8 h-8 flex items-center justify-center bg-card rounded-full shadow-sm text-text-muted hover:text-primary transition-colors cursor-pointer"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={onDelete}
            aria-label={`删除 ${character.name}`}
            className="w-8 h-8 flex items-center justify-center bg-card rounded-full shadow-sm text-text-muted hover:text-error transition-colors cursor-pointer"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <div className="flex flex-col gap-1.5 p-4">
        <h3 className="text-base font-bold text-text-primary">{character.name}</h3>
        <p className="text-xs text-text-muted leading-relaxed line-clamp-2">
          {character.appearance_prompt}
        </p>
      </div>
    </div>
  )
}
