import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Loader2, Route, BookMarked, Sparkles,
  AlertCircle, RefreshCw, FileDown, Printer,
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
  const [descExpanded, setDescExpanded] = useState(false)
  const [generateElapsed, setGenerateElapsed] = useState(0)
  const [generateProgress, setGenerateProgress] = useState(0)
  const [generateStage, setGenerateStage] = useState<string>('')

  // 清理 markdown 符号，避免影响观感
  const cleanMarkdown = useCallback((text: string) => {
    return (text || '')
      .replace(/#{1,6}\s*/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/^\s*[-•]\s*/gm, '• ')
      .replace(/\|/g, ' | ')
      .replace(/\s+/g, ' ')
      .trim()
  }, [])

  // 从 ai_analysis 解析实际调用模型（格式：## 文字分析（zhipu/glm-4-plus））
  const modelLabels = useMemo(() => {
    const textMatch = route?.ai_analysis?.match(/##\s*文字分析[（(]([^）)]+)[）)]/)
    const diagramMatch = route?.ai_analysis?.match(/##\s*研究架构图[（(]([^）)]+)[）)]/)
    return {
      text: textMatch?.[1] || '',
      diagram: diagramMatch?.[1] || '',
    }
  }, [route?.ai_analysis])

  // 导出 Word（.doc 排版 HTML）与 PDF（打印视图）
  const buildDocHtml = useCallback((r: ResearchRoute) => {
    const abs = (u: string) => (u.startsWith('/') ? `${window.location.origin}${u}` : u)
    const textClean = cleanMarkdown((r.ai_analysis || '').split(/##\s*研究架构图/)[0])
      .split('\n').filter(Boolean).map((l) => `<p style="margin:6px 0;line-height:1.8;">${l}</p>`).join('')
    const diagramRaw = (r.ai_analysis || '').split(/##\s*研究架构图/)[1] || ''
    const diagramText = cleanMarkdown(diagramRaw.replace(/!\[.*?\]\([^)]*\)/g, ''))
      .split('\n').filter(Boolean).map((l) => `<p style="margin:6px 0;line-height:1.8;">${l}</p>`).join('')
    const imgs = (r.ai_analysis || '').match(/!\[.*?\]\(((?:https?:\/\/|\/)[^)]+)\)/g) || []
    const imgTags = imgs.map((m) => {
      const url = m.replace(/^!\[.*?\]\(/, '').replace(/\)$/, '')
      return `<div style="margin:12px 0;text-align:center;"><img src="${abs(url)}" style="max-width:100%;border:1px solid #ddd;border-radius:8px;" /></div>`
    }).join('')
    const desc = cleanMarkdown(r.description || '').split('\n').filter(Boolean).map((l) => `<p style="margin:6px 0;line-height:1.8;">${l}</p>`).join('')
    const modelLine = [
      modelLabels.text ? `<span style="display:inline-block;margin-right:10px;padding:2px 10px;border-radius:999px;background:#eef2ff;color:#4f46e5;font-size:12px;">文字分析：${modelLabels.text}</span>` : '',
      modelLabels.diagram ? `<span style="display:inline-block;padding:2px 10px;border-radius:999px;background:#faf5ff;color:#7c3aed;font-size:12px;">架构图：${modelLabels.diagram}</span>` : '',
    ].filter(Boolean).join('')
    return `<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8" /><title>${r.title || '研究路线'}</title></head>
<body style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;color:#1a1b1c;max-width:820px;margin:0 auto;padding:32px 24px;">
  <h1 style="font-size:24px;margin-bottom:4px;">${r.title || ''}</h1>
  <p style="color:#6b7280;font-size:13px;margin-bottom:20px;">状态：${r.status || ''}${modelLine ? '　' + modelLine : ''}</p>
  <h2 style="font-size:18px;border-left:4px solid #4f46e5;padding-left:10px;margin:24px 0 8px;">路线描述</h2>
  ${desc || '<p style="color:#9ca3af;">无</p>'}
  <h2 style="font-size:18px;border-left:4px solid #4f46e5;padding-left:10px;margin:24px 0 8px;">AI 分析结果</h2>
  ${textClean}
  ${imgTags}
  ${diagramText ? `<h2 style="font-size:18px;border-left:4px solid #7c3aed;padding-left:10px;margin:24px 0 8px;">研究架构图描述</h2>${diagramText}` : ''}
  <p style="margin-top:32px;padding-top:12px;border-top:1px solid #eee;color:#9ca3af;font-size:12px;">由 ScholarNova 生成 · 模型与检索依据见上</p>
</body>
</html>`
  }, [cleanMarkdown, modelLabels.text, modelLabels.diagram])

  const handleExportDoc = useCallback(() => {
    if (!route) return
    const html = buildDocHtml(route)
    const blob = new Blob(['\ufeff' + html], { type: 'application/msword' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(route.title || '研究路线').replace(/[\\/:*?"<>|]/g, '_')}.doc`
    a.click()
    URL.revokeObjectURL(url)
  }, [route, buildDocHtml])

  const handleExportPdf = useCallback(() => {
    if (!route) return
    const html = buildDocHtml(route)
    const iframe = document.createElement('iframe')
    iframe.style.position = 'fixed'
    iframe.style.right = '0'
    iframe.style.bottom = '0'
    iframe.style.width = '0'
    iframe.style.height = '0'
    iframe.style.border = '0'
    document.body.appendChild(iframe)
    const doc = iframe.contentDocument || iframe.contentWindow?.document
    if (doc) {
      doc.open()
      doc.write(html)
      doc.close()
      setTimeout(() => {
        iframe.contentWindow?.focus()
        iframe.contentWindow?.print()
        setTimeout(() => iframe.remove(), 2000)
      }, 400)
    }
  }, [route, buildDocHtml])

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
    setGenerateElapsed(0)
    setGenerateProgress(0)
    setGenerateStage('')
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setGenerateElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 500)
    try {
      await knowledgeApi.generateRouteAnalysisStream(id, (evt) => {
        if (evt.progress != null) setGenerateProgress(evt.progress)
        if (evt.stage) setGenerateStage(evt.stage)
        if (evt.event === 'error') {
          toast.error(evt.message || t('common.error'))
        }
      })
      await fetchRoute()
      toast.success(isChinese ? '分析生成成功' : 'Analysis generated successfully')
    } catch {
      toast.error(t('common.error'))
    } finally {
      window.clearInterval(timer)
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
          <div className="flex items-center gap-2">
            {generating && (
              <span className="inline-flex items-center gap-1.5 text-xs text-primary-600 dark:text-primary-300 tabular-nums">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {generateProgress > 0 ? `${generateProgress}%` : '连接中...'} · {generateElapsed}s
              </span>
            )}
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
              {(() => {
                const cleanDesc = cleanMarkdown(route.description)
                const isLong = cleanDesc.length > 320
                const shown = descExpanded ? cleanDesc : cleanDesc.slice(0, 320) + (isLong ? '…' : '')
                return (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-line">
                      {shown}
                    </p>
                    {isLong && (
                      <button onClick={() => setDescExpanded(!descExpanded)}
                        className="mt-2 text-xs text-primary-600 dark:text-primary-400 hover:underline">
                        {descExpanded ? (isChinese ? '收起' : 'Show less') : (isChinese ? '展开完整路线描述' : 'Show full description')}
                      </button>
                    )}
                  </div>
                )
              })()}
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
          {generating && (
            <div className="mb-6 rounded-xl border border-blue-200 dark:border-blue-800/40 bg-blue-50 dark:bg-blue-900/20 p-4">
              <div className="flex items-center justify-between mb-2 text-sm text-blue-700 dark:text-blue-300">
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {generateStage === 'analysis' ? (isChinese ? 'AI 文字分析中...' : 'Analyzing...')
                    : generateStage === 'diagram' ? (isChinese ? '架构图生成中...' : 'Generating diagram...')
                    : generateStage === 'roadmap' ? (isChinese ? '科研阶段路线图生成中...' : 'Building roadmap...')
                    : (isChinese ? 'AI 分析中...' : 'AI analyzing...')}
                </span>
                <span className="tabular-nums">{generateProgress > 0 ? `${generateProgress}%` : ''} · 已用时 {generateElapsed}s</span>
              </div>
              <div className="h-1.5 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full transition-all duration-700"
                  style={{ width: `${Math.max(3, generateProgress)}%` }} />
              </div>
            </div>
          )}

          {/* AI Analysis */}
          {route.ai_analysis && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                  {isChinese ? 'AI 分析结果' : 'AI Analysis Results'}
                </h2>
                <div className="flex items-center gap-2 text-xs">
                  {modelLabels.text && (
                    <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium"
                      title="文字分析模型">{modelLabels.text}</span>
                  )}
                  {modelLabels.diagram && (
                    <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 font-medium"
                      title="架构图模型">{modelLabels.diagram}</span>
                  )}
                  <button onClick={handleExportDoc}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors font-medium"
                    title={isChinese ? '导出为 Word 文档' : 'Export as Word'}>
                    <FileDown className="w-3.5 h-3.5" />{isChinese ? '导出 Word' : 'Word'}
                  </button>
                  <button onClick={handleExportPdf}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors font-medium"
                    title={isChinese ? '打印 / 另存为 PDF' : 'Print / save as PDF'}>
                    <Printer className="w-3.5 h-3.5" />{isChinese ? '导出 PDF' : 'PDF'}
                  </button>
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
