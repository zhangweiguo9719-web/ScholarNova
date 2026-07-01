import { useState, useEffect } from 'react'
import {
  X, Loader2, Plus, Tag, FileText, BookOpen,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useLocaleStore } from '@/stores/localeStore'
import { knowledgeApi } from '@/api/client'
import type { KnowledgeItem, KnowledgeCreateRequest } from '@/api/types'
import './KnowledgeForm.css'

interface KnowledgeFormProps {
  open: boolean
  editingItem: KnowledgeItem | null
  prefill: Partial<KnowledgeItem> | null
  categories: { name: string; count: number }[]
  onClose: () => void
  onSuccess: () => void
}

export default function KnowledgeForm({
  open, editingItem, prefill, categories, onClose, onSuccess,
}: KnowledgeFormProps) {
  const { t, locale } = useLocaleStore()
  const isChinese = locale === 'zh'

  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [content, setContent] = useState('')
  const [sourcePaperTitle, setSourcePaperTitle] = useState('')
  const [sourcePaperDoi, setSourcePaperDoi] = useState('')
  const [researchPoints, setResearchPoints] = useState<string[]>([])
  const [researchPointInput, setResearchPointInput] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [showNewCategory, setShowNewCategory] = useState(false)

  // 从分析内容自动提取研究点和标签
  const extractFromContent = (text: string) => {
    if (!text) return { points: [] as string[], tags: [] as string[] }

    const points: string[] = []
    const tagSet = new Set<string>()

    // 提取研究点：匹配 "1. xxx" 或 "（1）xxx" 或 "- xxx" 格式
    const pointPatterns = [
      /(?:^|\n)\s*\d+[\.\)、]\s*(.+)/gm,
      /(?:^|\n)\s*[（(]\d+[)）]\s*(.+)/gm,
      /(?:^|\n)\s*[-•]\s*(.+)/gm,
      /(?:创新点|贡献|方法|发现|结论)[：:]\s*(.+)/g,
    ]
    for (const pattern of pointPatterns) {
      let match
      while ((match = pattern.exec(text)) !== null) {
        const point = match[1].trim().replace(/\*\*/g, '').slice(0, 80)
        if (point.length > 5 && !points.includes(point)) {
          points.push(point)
        }
      }
    }

    // 提取标签：技术术语
    const techTerms = [
      '联邦学习', '差分隐私', 'Transformer', 'GNN', 'CNN', 'RNN', 'LSTM',
      '注意力机制', '图神经网络', '强化学习', '迁移学习', '对比学习',
      '自监督', '预训练', '微调', '知识蒸馏', '模型压缩',
      '交通流', '预测', '时空', '图卷积', '自注意力',
      'federated learning', 'differential privacy', 'attention mechanism',
      'graph neural network', 'reinforcement learning', 'transfer learning',
      'traffic flow', 'prediction', 'spatio-temporal', 'transformer',
    ]
    const textLower = text.toLowerCase()
    for (const term of techTerms) {
      if (textLower.includes(term.toLowerCase())) {
        tagSet.add(term)
      }
    }

    // 从标题提取标签
    return { points: points.slice(0, 8), tags: Array.from(tagSet).slice(0, 10) }
  }

  useEffect(() => {
    if (editingItem) {
      setTitle(editingItem.title)
      setCategory(editingItem.category)
      setContent(editingItem.content)
      setSourcePaperTitle(editingItem.source_paper_title || '')
      setSourcePaperDoi(editingItem.source_paper_doi || '')
      setResearchPoints(editingItem.research_points)
      setTags(editingItem.tags)
      setNotes(editingItem.notes || '')
      setShowNewCategory(false)
      setNewCategory('')
    } else if (prefill) {
      setTitle(prefill.title || '')
      setCategory(prefill.category || '')
      setContent(prefill.content || '')
      setSourcePaperTitle(prefill.source_paper_title || '')
      setSourcePaperDoi(prefill.source_paper_doi || '')
      // 如果没有预填的研究点和标签，从内容自动提取
      if ((!prefill.research_points || prefill.research_points.length === 0) && prefill.content) {
        const extracted = extractFromContent(prefill.content)
        setResearchPoints(extracted.points)
        setTags(extracted.tags)
      } else {
        setResearchPoints(prefill.research_points || [])
        setTags(prefill.tags || [])
      }
      setNotes(prefill.notes || '')
      setShowNewCategory(false)
      setNewCategory('')
    } else {
      resetForm()
    }
  }, [editingItem, prefill, open])

  const resetForm = () => {
    setTitle('')
    setCategory('')
    setContent('')
    setSourcePaperTitle('')
    setSourcePaperDoi('')
    setResearchPoints([])
    setResearchPointInput('')
    setTags([])
    setTagInput('')
    setNotes('')
    setShowNewCategory(false)
    setNewCategory('')
  }

  const handleResearchPointKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const val = researchPointInput.trim()
      if (val && !researchPoints.includes(val)) {
        setResearchPoints([...researchPoints, val])
        setResearchPointInput('')
      }
    }
  }

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const val = tagInput.trim()
      if (val && !tags.includes(val)) {
        setTags([...tags, val])
        setTagInput('')
      }
    }
  }

  const removeResearchPoint = (idx: number) => {
    setResearchPoints(researchPoints.filter((_, i) => i !== idx))
  }

  const removeTag = (idx: number) => {
    setTags(tags.filter((_, i) => i !== idx))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      toast.error(isChinese ? '请输入标题' : 'Please enter a title')
      return
    }

    const finalCategory = showNewCategory ? newCategory.trim() : category
    if (!finalCategory) {
      toast.error(isChinese ? '请选择或输入分类' : 'Please select or enter a category')
      return
    }

    setSaving(true)
    try {
      const hasSourcePaper = !!(editingItem?.source_paper_id || prefill?.source_paper_id)
      const data: KnowledgeCreateRequest = {
        title: title.trim(),
        category: finalCategory,
        content: content.trim(),
        source_paper_title: sourcePaperTitle.trim() || null,
        source_paper_doi: sourcePaperDoi.trim() || null,
        source_paper_id: editingItem?.source_paper_id || prefill?.source_paper_id || null,
        research_points: researchPoints,
        tags,
        notes: notes.trim() || null,
        auto_polish: hasSourcePaper && !editingItem, // 从论文分析保存时自动润色
      }

      if (editingItem) {
        await knowledgeApi.update(editingItem.id, data)
      } else {
        await knowledgeApi.create(data)
      }
      toast.success(t('knowledge.saveSuccess'))
      onSuccess()
      onClose()
    } catch {
      toast.error(t('knowledge.saveError'))
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="knowledge-form-overlay" onClick={onClose}>
      <div className="knowledge-form animate-fade-in" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="knowledge-form-header">
          <h2 className="knowledge-form-title">
            {editingItem ? t('knowledge.editTitle') : t('knowledge.createTitle')}
          </h2>
          <button onClick={onClose} className="knowledge-form-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="knowledge-form-body custom-scrollbar">
          {/* Title */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <FileText className="w-4 h-4" />
              {t('knowledge.titleField')} *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('knowledge.titlePlaceholder')}
              className="knowledge-form-input"
            />
          </div>

          {/* Category */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <FileText className="w-4 h-4" />
              {t('knowledge.category')} *
            </label>
            {!showNewCategory ? (
              <div className="flex gap-2">
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="knowledge-form-input flex-1"
                >
                  <option value="">{t('knowledge.categorySelect')}</option>
                  {categories.map((cat) => (
                    <option key={cat.name} value={cat.name}>{cat.name} ({cat.count})</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setShowNewCategory(true)}
                  className="knowledge-form-add-btn"
                  title={t('knowledge.categoryNew')}
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  placeholder={t('knowledge.categoryNewPlaceholder')}
                  className="knowledge-form-input flex-1"
                />
                <button
                  type="button"
                  onClick={() => { setShowNewCategory(false); setNewCategory('') }}
                  className="knowledge-form-cancel-btn"
                >
                  {t('common.cancel')}
                </button>
              </div>
            )}
          </div>

          {/* Source Paper */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <BookOpen className="w-4 h-4" />
              {t('knowledge.sourcePaper')} {t('knowledge.sourcePaperOptional')}
            </label>
            <input
              type="text"
              value={sourcePaperTitle}
              onChange={(e) => setSourcePaperTitle(e.target.value)}
              placeholder={t('knowledge.sourcePaperTitle')}
              className="knowledge-form-input"
            />
            <input
              type="text"
              value={sourcePaperDoi}
              onChange={(e) => setSourcePaperDoi(e.target.value)}
              placeholder={t('knowledge.sourcePaperDOI')}
              className="knowledge-form-input mt-2"
            />
          </div>

          {/* Content */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <FileText className="w-4 h-4" />
              {t('knowledge.content')}
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={t('knowledge.contentPlaceholder')}
              rows={6}
              className="knowledge-form-textarea"
            />
          </div>

          {/* Research Points */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <FileText className="w-4 h-4" />
              {t('knowledge.researchPoints')}
            </label>
            {researchPoints.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {researchPoints.map((point, i) => (
                  <span key={i} className="knowledge-tag">
                    {point}
                    <button type="button" onClick={() => removeResearchPoint(i)} className="knowledge-tag-remove">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <input
                type="text"
                value={researchPointInput}
                onChange={(e) => setResearchPointInput(e.target.value)}
                onKeyDown={handleResearchPointKeyDown}
                placeholder={t('knowledge.researchPointsPlaceholder')}
                className="knowledge-form-input flex-1"
              />
            </div>
            <p className="knowledge-form-hint">{t('knowledge.researchPointsHint')}</p>
          </div>

          {/* Tags */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <Tag className="w-4 h-4" />
              {t('knowledge.tags')}
            </label>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {tags.map((tag, i) => (
                  <span key={i} className="knowledge-tag">
                    #{tag}
                    <button type="button" onClick={() => removeTag(i)} className="knowledge-tag-remove">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder={t('knowledge.tagsPlaceholder')}
                className="knowledge-form-input flex-1"
              />
            </div>
            <p className="knowledge-form-hint">{t('knowledge.tagsHint')}</p>
          </div>

          {/* Notes */}
          <div className="knowledge-form-field">
            <label className="knowledge-form-label">
              <FileText className="w-4 h-4" />
              {t('knowledge.notes')}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t('knowledge.notesPlaceholder')}
              rows={3}
              className="knowledge-form-textarea"
            />
          </div>
        </form>

        {/* Footer */}
        <div className="knowledge-form-footer">
          <button onClick={onClose} className="knowledge-form-cancel-btn">
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="knowledge-form-submit-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {t('knowledge.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
