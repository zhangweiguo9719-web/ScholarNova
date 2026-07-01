import { useState } from 'react'
import {
  X, Edit2, Trash2, ExternalLink, Tag, FileText,
  BookOpen, Clock, StickyNote, Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useLocaleStore } from '@/stores/localeStore'
import { knowledgeApi } from '@/api/client'
import type { KnowledgeItem } from '@/api/types'
import './KnowledgeDetail.css'

interface KnowledgeDetailProps {
  item: KnowledgeItem
  onClose: () => void
  onEdit: (item: KnowledgeItem) => void
  onDelete: (id: string) => void
}

export default function KnowledgeDetail({
  item, onClose, onEdit, onDelete,
}: KnowledgeDetailProps) {
  const { t, locale } = useLocaleStore()
  const isChinese = locale === 'zh'
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!window.confirm(t('knowledge.deleteConfirm'))) return
    setDeleting(true)
    try {
      await knowledgeApi.delete(item.id)
      toast.success(t('knowledge.deleteSuccess'))
      onDelete(item.id)
      onClose()
    } catch {
      toast.error(t('knowledge.deleteError'))
    } finally {
      setDeleting(false)
    }
  }

  const renderAnalysisContent = (text: string) => {
    const sections = text.split(/\n(?=\d+[\.\)、]|#{1,3}\s|\*\*[^*]+\*\*)/g).filter(Boolean)
    return sections.map((section, i) => {
      const headingMatch = section.match(/^(?:\d+[\.\)、]|#{1,3}\s|\*\*)(.+?)(?:\*\*|$)/m)
      const heading = headingMatch ? headingMatch[1].replace(/\*\*/g, '').trim() : null
      const body = heading ? section.slice(section.indexOf(heading) + heading.length).trim() : section.trim()
      return (
        <div key={i} className="mb-3">
          {heading && <h5 className="text-xs font-bold text-primary-600 dark:text-primary-400 mb-1">{heading}</h5>}
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">{body}</p>
        </div>
      )
    })
  }

  return (
    <div className="knowledge-detail animate-fade-in">
      {/* Header */}
      <div className="knowledge-detail-header">
        <div className="flex-1 min-w-0">
          <h2 className="knowledge-detail-title">{item.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
              <FileText className="w-3 h-3" />
              {item.category || (isChinese ? '未分类' : 'Uncategorized')}
            </span>
          </div>
        </div>
        <button onClick={onClose} className="knowledge-detail-close">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Meta */}
      <div className="knowledge-detail-meta">
        <div className="meta-row">
          <Clock className="w-4 h-4" />
          <span>{isChinese ? '创建: ' : 'Created: '}{new Date(item.created_at).toLocaleDateString()}</span>
        </div>
        {item.updated_at !== item.created_at && (
          <div className="meta-row">
            <Clock className="w-4 h-4" />
            <span>{isChinese ? '更新: ' : 'Updated: '}{new Date(item.updated_at).toLocaleDateString()}</span>
          </div>
        )}
      </div>

      {/* Source Paper */}
      {item.source_paper_title && (
        <div className="knowledge-detail-section">
          <h4 className="knowledge-detail-section-title">
            <BookOpen className="w-4 h-4" />
            {t('knowledge.sourcePaper')}
          </h4>
          <div className="knowledge-source-paper">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.source_paper_title}</p>
            {item.source_paper_doi && (
              <a
                href={`https://doi.org/${item.source_paper_doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline mt-1"
              >
                <ExternalLink className="w-3 h-3" />
                {item.source_paper_doi}
              </a>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="knowledge-detail-content custom-scrollbar">
        <div className="knowledge-detail-section">
          <h4 className="knowledge-detail-section-title">
            <FileText className="w-4 h-4" />
            {t('knowledge.content')}
          </h4>
          <div className="knowledge-content-body">
            {renderAnalysisContent(item.content)}
          </div>
        </div>

        {/* Research Points */}
        {item.research_points.length > 0 && (
          <div className="knowledge-detail-section">
            <h4 className="knowledge-detail-section-title">
              <StickyNote className="w-4 h-4" />
              {t('knowledge.researchPoints')}
            </h4>
            <ul className="space-y-1">
              {item.research_points.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <span className="text-primary-500 mt-0.5">&#x2022;</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Tags */}
        {item.tags.length > 0 && (
          <div className="knowledge-detail-section">
            <h4 className="knowledge-detail-section-title">
              <Tag className="w-4 h-4" />
              {t('knowledge.tags')}
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {item.tags.map((tag, i) => (
                <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {item.notes && (
          <div className="knowledge-detail-section">
            <h4 className="knowledge-detail-section-title">
              <StickyNote className="w-4 h-4" />
              {t('knowledge.notes')}
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line bg-yellow-50 dark:bg-yellow-900/10 p-3 rounded-md border border-yellow-200 dark:border-yellow-800">
              {item.notes}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="knowledge-detail-actions">
        <button
          onClick={() => onEdit(item)}
          className="knowledge-action-btn knowledge-action-edit"
        >
          <Edit2 className="w-4 h-4" />
          {t('knowledge.edit')}
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="knowledge-action-btn knowledge-action-delete"
        >
          {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
          {t('knowledge.delete')}
        </button>
      </div>
    </div>
  )
}
