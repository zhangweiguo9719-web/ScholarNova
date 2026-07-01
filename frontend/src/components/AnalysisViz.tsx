/**
 * AI 分析结果可视化组件
 * MiMo 文字分析 + SenseNova U1 图片
 */
import { useState, useEffect } from 'react'
import { Clock, Sparkles, FlaskConical } from 'lucide-react'
import clsx from 'clsx'
import { useLocaleStore } from '@/stores/localeStore'

interface AnalysisVizProps {
  analysis: string
  loading?: boolean
  estimatedTime?: number
}

function renderMarkdownText(text: string) {
  // 先清理 markdown 标记
  const lines = text
    .replace(/#{4}\s*/g, '')  // ####
    .replace(/#{3}\s*/g, '')  // ###
    .replace(/#{2}\s*/g, '')  // ##
    .replace(/#{1}\s*/g, '')  // #
    .split('\n')

  return lines.map((line, i) => {
    const trimmed = line.trim()
    if (!trimmed) return null

    // 标题行（原 ## 开头的）
    const isHeading = /^[一-龥].*[:：]$/.test(trimmed) ||
      /^[一-龥].*任务|^[一-龥].*目标|^[一-龥].*模块|^[一-龥].*阶段/.test(trimmed)

    // 清理 ** 加粗标记
    const cleanLine = trimmed.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*([^*]+)\*/g, '$1')

    if (isHeading) {
      return (
        <h5 key={i} className="text-sm font-bold text-primary-700 dark:text-primary-300 mt-3 mb-1 border-l-2 border-primary-400 pl-2">
          {cleanLine}
        </h5>
      )
    }

    // 编号列表
    if (/^\d+[\.\)、]/.test(cleanLine)) {
      return (
        <p key={i} className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-1 pl-4">
          {cleanLine}
        </p>
      )
    }

    // 列表项
    if (/^[-•]\s/.test(cleanLine)) {
      return (
        <p key={i} className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-0.5 pl-6 flex items-start gap-1">
          <span className="text-primary-400 mt-0.5 flex-shrink-0">-</span>
          {cleanLine.replace(/^[-•]\s*/, '')}
        </p>
      )
    }

    // 普通段落
    return (
      <p key={i} className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-1">
        {cleanLine}
      </p>
    )
  }).filter(Boolean)
}

function WaitTimer({ seconds }: { seconds: number }) {
  const [remaining, setRemaining] = useState(seconds)
  const [step, setStep] = useState(0)
  const steps = ['MiMo 文字分析...', 'SenseNova 图表生成...', '渲染结果...']

  useEffect(() => {
    const timer = setInterval(() => {
      setRemaining(r => r <= 1 ? (clearInterval(timer), 0) : r - 1)
      setStep(s => Math.min(s + 1, 2))
    }, (seconds / 3) * 1000)
    return () => clearInterval(timer)
  }, [seconds])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800/30">
        <Clock className="w-4 h-4 text-blue-500 animate-pulse" />
        <span className="text-sm text-blue-700 dark:text-blue-300">
          {remaining > 0 ? `预计还需 ${remaining} 秒...` : '即将完成...'}
        </span>
        <div className="flex-1 h-1.5 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden ml-2">
          <div className="h-full bg-blue-500 rounded-full transition-all duration-1000"
            style={{ width: `${Math.max(0, (remaining / seconds) * 100)}%` }} />
        </div>
      </div>
      <div className="flex gap-2 text-xs">
        {steps.map((s, i) => (
          <span key={i} className={clsx('px-2 py-1 rounded-full transition-colors',
            i <= step ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-400')}>
            {i < step ? '✓' : i === step ? '⏳' : '○'} {s}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function AnalysisViz({
  analysis, loading = false, estimatedTime = 60,
}: AnalysisVizProps) {
  const { locale } = useLocaleStore()
  const isChinese = locale === 'zh'
  const [showFull, setShowFull] = useState(false)

  if (loading) return <WaitTimer seconds={estimatedTime} />

  // 从全文中提取所有图片 URL
  const imageUrls: string[] = []
  const patterns = [
    /!\[.*?\]\((https?:\/\/[^)]+)\)/g,                          // markdown 图片
    /\[.*?\]\((https?:\/\/[^\)]+\.(png|jpg|jpeg|webp|gif)[^\)]*)\)/gi, // 带后缀链接
    /(https?:\/\/[^\s)]+\.(png|jpg|jpeg|webp|gif)[^\s)]*)/gi,    // 裸图片 URL
  ]
  for (const p of patterns) {
    let m
    while ((m = p.exec(analysis)) !== null) {
      const url = m[1] || m[0]
      if (url && !imageUrls.includes(url)) imageUrls.push(url)
    }
  }
  // 补充匹配 SenseNova OSS 域名（无后缀的 UUID 图片）
  const ossRegex = /(https?:\/\/aoss\.cn-sh-01\.sensecoreapi-oss\.cn\/[^\s)\]>"]+)/gi
  let m2
  while ((m2 = ossRegex.exec(analysis)) !== null) {
    if (m2[1] && !imageUrls.includes(m2[1])) imageUrls.push(m2[1])
  }

  // 分离 MiMo 文字和 SenseNova 图片
  const textPart = analysis.split(/##\s*研究架构图/)[0] || analysis
  const diagramPart = analysis.includes('研究架构图') ? analysis.split(/##\s*研究架构图/)[1] || '' : ''

  return (
    <div className="space-y-4">
      {/* MiMo 文字分析 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary-500" />
          {isChinese ? 'MiMo 文字分析' : 'MiMo Text Analysis'}
        </h3>
        <div className="relative">
          <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary-500 to-primary-300" />
          <div className="pl-8">
            {renderMarkdownText(showFull ? textPart : textPart.slice(0, 2000))}
            {textPart.length > 2000 && (
              <button onClick={() => setShowFull(!showFull)}
                className="mt-2 text-xs text-primary-600 dark:text-primary-400 hover:underline">
                {showFull ? (isChinese ? '收起' : 'Show less') : (isChinese ? '展开全部' : 'Show all')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* SenseNova 架构图 */}
      {imageUrls.length > 0 ? (
        imageUrls.map((url, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <FlaskConical className="w-4 h-4 text-purple-500" />
              {isChinese ? 'SenseNova-U1 研究架构图' : 'SenseNova-U1 Architecture'}
            </h3>
            <img src={url} alt={isChinese ? '研究架构图' : 'Architecture'}
              className="w-full rounded-lg shadow-md cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => window.open(url, '_blank')} />
            <a href={url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline mt-2">
              {isChinese ? '🔍 查看大图' : '🔍 View full size'}
            </a>
          </div>
        ))
      ) : diagramPart && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-purple-500" />
            {isChinese ? 'SenseNova-U1 研究架构图' : 'SenseNova-U1 Architecture'}
          </h3>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            {renderMarkdownText(diagramPart)}
          </div>
        </div>
      )}
    </div>
  )
}
