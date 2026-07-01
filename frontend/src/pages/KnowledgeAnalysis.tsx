import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, Loader2, AlertCircle,
  FolderOpen, ChevronDown, ChevronRight, CheckCircle,
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useLocaleStore } from '@/stores/localeStore'
import AnalysisViz from '@/components/AnalysisViz'
import { knowledgeApi } from '@/api/client'
import type { KnowledgeItem, AIAnalyzeResponse } from '@/api/types'
import './KnowledgeAnalysis.css'

// 分析结果持久化到 localStorage
const STORAGE_KEY = 'scholar-analysis-result'

export default function KnowledgeAnalysis() {
  const navigate = useNavigate()
  const { t, locale } = useLocaleStore()
  const isChinese = locale === 'zh'

  const [categories, setCategories] = useState<{ name: string; count: number }[]>([])
  const [categoryItems, setCategoryItems] = useState<Record<string, KnowledgeItem[]>>({})
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AIAnalyzeResponse | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        // 只恢复文本结果，不恢复大对象
        return { analysis: parsed.analysis || '', research_directions: parsed.research_directions || [], architecture_description: parsed.architecture_description || '', suggested_routes: parsed.suggested_routes || [], recommended_papers: parsed.recommended_papers || [], knowledge_count: parsed.knowledge_count || 0, created_at: parsed.created_at || '' }
      }
    } catch {}
    return null
  })
  const [error, setError] = useState<string | null>(null)

  const fetchCategories = useCallback(async () => {
    setLoading(true)
    try {
      const response = await knowledgeApi.getCategories()
      setCategories(response.data)
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchCategories() }, [fetchCategories])

  // 展开分类时加载其条目
  const toggleCategory = async (catName: string) => {
    if (expandedCategory === catName) {
      setExpandedCategory(null)
      return
    }
    setExpandedCategory(catName)
    if (!categoryItems[catName]) {
      try {
        const response = await knowledgeApi.list(catName)
        setCategoryItems((prev) => ({ ...prev, [catName]: response.data.items }))
        // 全选该分类
        setSelectedIds(response.data.items.map((i) => i.id))
      } catch {
        toast.error(t('common.error'))
      }
    }
  }

  const toggleItem = (id: string) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id])
  }

  const toggleAllInCategory = (catName: string) => {
    const items = categoryItems[catName] || []
    const allSelected = items.every((i) => selectedIds.includes(i.id))
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !items.find((i) => i.id === id)))
    } else {
      setSelectedIds((prev) => [...new Set([...prev, ...items.map((i) => i.id)])])
    }
  }

  // 自动保存分析结果为卡片
  const saveAnalysisAsCards = async (analysis: AIAnalyzeResponse) => {
    try {
      // 获取选中知识点的分类
      let category = 'AI分析'
      for (const catName of Object.keys(categoryItems)) {
        const catItems = categoryItems[catName]
        if (catItems?.some((i) => selectedIds.includes(i.id))) {
          category = catName
          break
        }
      }

      // 保存研究方向卡片
      if (analysis.research_directions?.length) {
        for (const dir of analysis.research_directions) {
          await knowledgeApi.create({
            title: dir.slice(0, 100),
            category,
            content: dir,
            card_type: 'direction',
            card_data: { direction: dir },
            tags: ['AI分析', '研究方向'],
            research_points: [dir],
            source_paper_title: `AI分析 - ${category}`,
          })
        }
      }

      // 保存架构图卡片
      if (analysis.architecture_description) {
        await knowledgeApi.create({
          title: `${category} - 研究架构图`,
          category,
          content: analysis.architecture_description,
          card_type: 'architecture',
          card_data: { architecture: analysis.architecture_description },
          tags: ['AI分析', '架构图'],
          source_paper_title: `AI分析 - ${category}`,
        })
      }

      // 保存推荐论文卡片
      if (analysis.recommended_papers?.length) {
        for (const paper of analysis.recommended_papers) {
          await knowledgeApi.create({
            title: paper.slice(0, 100),
            category,
            content: paper,
            card_type: 'paper',
            card_data: { recommendation: paper },
            tags: ['AI分析', '推荐论文'],
            source_paper_title: `AI推荐 - ${category}`,
          })
        }
      }

      toast.success(isChinese ? '分析结果已保存为知识卡片' : 'Analysis saved as knowledge cards')

      // 自动创建研究路线
      const firstCat = selectedIds.length > 0 ? Object.keys(categoryItems).find((cat) =>
        categoryItems[cat]?.some((i) => selectedIds.includes(i.id))
      ) : null
      const routeTitle = firstCat || (isChinese ? '研究路线' : 'Research Route')

      try {
        await knowledgeApi.createRoute({
          title: routeTitle,
          description: analysis.analysis?.slice(0, 200) || '',
          knowledge_ids: selectedIds,
        })
        toast.success(isChinese ? `已自动创建研究路线「${routeTitle}」` : `Auto-created route "${routeTitle}"`)
      } catch {
        // 路线创建失败不影响主流程
      }
    } catch (err) {
      console.error('Failed to save analysis cards:', err)
    }
  }

  const handleAnalyze = async () => {
    if (selectedIds.length === 0) {
      toast.error(isChinese ? '请至少选择一个知识点' : 'Select at least one item')
      return
    }
    setAnalyzing(true)
    setError(null)
    console.log('Calling aiAnalyze with IDs:', selectedIds)
    try {
      const response = await knowledgeApi.aiAnalyze(selectedIds)
      console.log('Response:', response.data)
      setResult(response.data)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(response.data))
      // 自动保存为卡片
      await saveAnalysisAsCards(response.data)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || t('common.error')
      setError(msg)
      toast.error(msg)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <button onClick={() => navigate('/knowledge')}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <Sparkles className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">{t('knowledge.aiAnalysis')}</h1>
          {selectedIds.length > 0 && !result && (
            <span className="ml-auto text-xs text-gray-500">{isChinese ? `已选 ${selectedIds.length} 个` : `${selectedIds.length} selected`}</span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {!result ? (
            <>
              <div className="mb-4">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                  {isChinese ? '展开分类选择知识点，然后点击分析' : 'Expand categories to select items, then click analyze'}
                </p>
              </div>

              {loading ? (
                <div className="space-y-2">{[1, 2].map((i) => <div key={i} className="skeleton h-14 rounded-lg" />)}</div>
              ) : categories.length === 0 ? (
                <div className="text-center py-8 text-gray-400">{isChinese ? '知识库为空' : 'Empty knowledge base'}</div>
              ) : (
                <div className="space-y-2">
                  {categories.map((cat) => {
                    const isExpanded = expandedCategory === cat.name
                    const items = categoryItems[cat.name] || []
                    const allSelected = items.length > 0 && items.every((i) => selectedIds.includes(i.id))

                    return (
                      <div key={cat.name} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                        <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/50">
                          <button onClick={() => toggleCategory(cat.name)} className="flex items-center gap-2 flex-1 text-left">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            <FolderOpen className="w-4 h-4 text-primary-500" />
                            <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{cat.name}</span>
                            <span className="text-xs text-gray-400">({cat.count})</span>
                          </button>
                          {isExpanded && items.length > 0 && (
                            <button onClick={() => toggleAllInCategory(cat.name)}
                              className="text-xs text-primary-600 dark:text-primary-400 hover:underline px-2">
                              {allSelected ? (isChinese ? '取消全选' : 'Deselect') : (isChinese ? '全选' : 'Select All')}
                            </button>
                          )}
                        </div>
                        {isExpanded && (
                          <div className="border-t border-gray-200 dark:border-gray-700">
                            {items.length === 0 ? (
                              <div className="p-3 text-sm text-gray-400 text-center">{isChinese ? '加载中...' : 'Loading...'}</div>
                            ) : (
                              <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
                                {items.map((item) => (
                                  <button key={item.id} onClick={() => toggleItem(item.id)}
                                    className={clsx('w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                                      selectedIds.includes(item.id) ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800/30')}>
                                    <div className={clsx('w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0',
                                      selectedIds.includes(item.id) ? 'border-primary-500 bg-primary-500' : 'border-gray-300 dark:border-gray-600')}>
                                      {selectedIds.includes(item.id) && <CheckCircle className="w-3 h-3 text-white" />}
                                    </div>
                                    <span className="text-sm text-gray-700 dark:text-gray-300 truncate">{item.title}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              <div className="flex justify-center mt-6">
                <button onClick={handleAnalyze} disabled={analyzing || selectedIds.length === 0}
                  className={clsx('inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-lg transition-colors',
                    analyzing || selectedIds.length === 0 ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed' : 'bg-primary-600 text-white hover:bg-primary-700')}>
                  {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {analyzing ? (isChinese ? '分析中...' : 'Analyzing...') : (isChinese ? 'AI 分析研究方向' : 'AI Research Analysis')}
                </button>
              </div>

              {error && (
                <div className="mt-4 flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
                  <AlertCircle className="w-4 h-4" />{error}
                </div>
              )}
            </>
          ) : (
            <div className="animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">{t('knowledge.aiResultTitle')}</h2>
                <button onClick={() => { setResult(null); setSelectedIds([]); localStorage.removeItem(STORAGE_KEY) }}
                  className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
                  {isChinese ? '重新分析' : 'Re-analyze'}
                </button>
              </div>

              <AnalysisViz
                analysis={result.analysis || ''}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
