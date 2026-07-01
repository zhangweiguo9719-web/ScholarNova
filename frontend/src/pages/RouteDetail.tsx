import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Loader2, Route, BookMarked, Sparkles,
  AlertCircle, RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useLocaleStore } from '@/stores/localeStore'
import { knowledgeApi } from '@/api/client'
import type { ResearchRoute, KnowledgeItem } from '@/api/types'
import AnalysisViz from '@/components/AnalysisViz'
import './KnowledgeAnalysis.css'

export default function RouteDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t, locale } = useLocaleStore()
  const isChinese = locale === 'zh'

  const [route, setRoute] = useState<ResearchRoute | null>(null)
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRoute = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const response = await knowledgeApi.getRoute(id)
      setRoute(response.data)
      // Fetch related knowledge items
      if (response.data.knowledge_ids && response.data.knowledge_ids.length > 0) {
        try {
          const allItems = await knowledgeApi.list()
          const related = allItems.data.items.filter((item) =>
            response.data.knowledge_ids.includes(item.id)
          )
          setKnowledgeItems(related)
        } catch {
          // Knowledge items may not be available
        }
      }
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchRoute()
  }, [fetchRoute])

  const handleGenerate = async () => {
    if (!id) return
    setGenerating(true)
    try {
      const response = await knowledgeApi.generateRouteAnalysis(id)
      setRoute(response.data)
      toast.success(isChinese ? '分析生成成功' : 'Analysis generated successfully')
    } catch {
      toast.error(t('common.error'))
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="h-[calc(100vh-3.5rem)] flex flex-col">
        <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
          <div className="max-w-4xl mx-auto flex items-center gap-3">
            <button onClick={() => navigate('/knowledge')} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Route className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">{t('knowledge.routeDetail')}</h1>
            </div>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      </div>
    )
  }

  if (error || !route) {
    return (
      <div className="h-[calc(100vh-3.5rem)] flex flex-col">
        <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
          <div className="max-w-4xl mx-auto flex items-center gap-3">
            <button onClick={() => navigate('/knowledge')} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Route className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">{t('knowledge.routeDetail')}</h1>
            </div>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <AlertCircle className="w-12 h-12 text-red-300" />
          <p className="text-gray-500">{error || t('common.noData')}</p>
          <button onClick={fetchRoute} className="text-sm text-primary-600 hover:underline">{t('common.retry')}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/knowledge')} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Route className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">{route.title}</h1>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {generating ? t('knowledge.routeGenerating') : t('knowledge.routeGenerate')}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {/* Description */}
          {route.description && (
            <div className="analysis-section mb-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                {t('knowledge.routeDescription')}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {route.description}
              </p>
            </div>
          )}

          {/* Status */}
          <div className="flex items-center gap-3 mb-6">
            <span className="text-xs font-medium text-gray-500">{t('knowledge.routeStatus')}:</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400">
              {route.status}
            </span>
          </div>

          {/* AI Analysis */}
          {route.ai_analysis && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                  {isChinese ? 'AI 分析结果' : 'AI Analysis Results'}
                </h2>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium">MiMo</span>
                  <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 font-medium">SenseNova</span>
                </div>
              </div>
              <AnalysisViz
                analysis={route.ai_analysis}
              />
            </div>
          )}

          {/* Related Knowledge */}
          {knowledgeItems.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                <BookMarked className="w-4 h-4 text-primary-500" />
                {t('knowledge.routeKnowledge')} ({knowledgeItems.length})
              </h2>
              <div className="space-y-2">
                {knowledgeItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  >
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.title}</h4>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {item.category}
                      {item.tags.length > 0 && ` | ${item.tags.map((t) => `#${t}`).join(' ')}`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {!route.ai_analysis && knowledgeItems.length === 0 && (
            <div className="text-center py-12">
              <Route className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">
                {isChinese ? '点击上方按钮生成 AI 分析' : 'Click the button above to generate AI analysis'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
