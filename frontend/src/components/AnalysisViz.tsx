/**
 * AI 分析结果可视化组件
 * Provider-neutral text analysis + configured diagram model
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

function parseLayers(text: string): { title: string; modules: string[] }[] {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const layers: { title: string; modules: string[] }[] = []
  let current: { title: string; modules: string[] } | null = null
  for (const line of lines) {
    const clean = line.replace(/^[-*#>#\s]+/, '').replace(/\*\*/g, '')
    if (!clean) continue
    const isLayerTitle = (/(层|阶段|模块组|环节|编码器|解码器|Layer|Stage|Phase|Core|Input|Output)/.test(clean) || /[:：]$/.test(clean)) && !clean.includes('|') && clean.length <= 40
    if (isLayerTitle) {
      current = { title: clean.replace(/[:：]\s*$/, ''), modules: [] }
      layers.push(current)
    } else if (current) {
      if (clean.includes('|')) {
        current.modules.push(...clean.split('|').map((m) => m.trim()).filter(Boolean))
      } else if (clean.length > 2 && !/^(图|表|注|说明)/.test(clean)) {
        current.modules.push(clean)
      }
    }
  }
  return layers.filter((l) => l.title || l.modules.length > 0)
}

function ArchitectureSvg({ text }: { text: string }) {
  const cleaned = text.replace(/^\s*\d+[.、)]?\s*研究架构图[（(]?[^）)]*[）)]?\s*[\r\n]*/m, '').trim()
  const layers = parseLayers(cleaned)
  if (layers.length === 0) {
    return (
      <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">
        {text.replace(/#{1,4}\s*/g, '').replace(/\*\*([^*]+)\*\*/g, '$1')}
      </div>
    )
  }
  // SVG 布局参数
  const width = 760
  const modX = 220
  const modW = 160
  const modH = 34
  const gap = 12
  const perRow = Math.max(1, Math.floor((width - modX - 24) / (modW + gap)))
  const rowH = modH + 8
  const padTop = 14
  const arrowH = 30
  const colors = ['#eaf2fb', '#e8f6ef', '#fbf1e7', '#f1eafa', '#e7f5f7', '#fdf3e6']
  const borders = ['#8bc8ea', '#94d8c3', '#f4b393', '#c9a7e8', '#a3d5e8', '#e4d48f']

  // 计算每层高度
  const layerRows = layers.map((l) => Math.max(1, Math.ceil(l.modules.length / perRow)))
  const layerHeights = layerRows.map((rows) => padTop + rows * rowH + 8)
  const totalH = layerHeights.reduce((a, b) => a + b, 0) + arrowH * (layers.length - 1) + 16

  let y = 8
  const boxes: React.ReactNode[] = []
  layers.forEach((layer, li) => {
    const layerH = layerHeights[li]
    const color = colors[li % colors.length]
    const border = borders[li % borders.length]
    // 层背景
    boxes.push(
      <rect key={`bg${li}`} x={6} y={y} width={width - 12} height={layerH} rx={12}
        fill={color} stroke={border} strokeWidth={1.2} />,
    )
    // 层标题（竖排居左）
    const midY = y + layerH / 2
    const titleLines = layer.title.length > 10
      ? [layer.title.slice(0, Math.ceil(layer.title.length / 2)), layer.title.slice(Math.ceil(layer.title.length / 2))]
      : [layer.title]
    titleLines.forEach((tl, ti) => {
      boxes.push(
        <text key={`t${li}-${ti}`} x={22} y={midY + (titleLines.length === 1 ? 5 : (ti - 0.5) * 15)}
          fontSize={14} fontWeight={700} fill="#334155">
          {tl}
        </text>,
      )
    })
    // 模块 chip
    layer.modules.slice(0, 14).forEach((mod, mi) => {
      const row = Math.floor(mi / perRow)
      const col = mi % perRow
      const cx = modX + col * (modW + gap)
      const cy = y + padTop + row * rowH
      boxes.push(
        <rect key={`m${li}-${mi}`} x={cx} y={cy} width={modW} height={modH} rx={8}
          fill="#ffffff" stroke={border} strokeWidth={1} />,
      )
      const label = mod.length > 18 ? mod.slice(0, 17) + '…' : mod
      boxes.push(
        <text key={`mt${li}-${mi}`} x={cx + modW / 2} y={cy + modH / 2 + 4.5}
          fontSize={11.5} fill="#334155" textAnchor="middle" fontWeight={500}>
          {label}
        </text>,
      )
    })
    // 层间箭头（垂直向下）
    if (li < layers.length - 1) {
      const fromY = y + layerH
      const toY = fromY + arrowH
      const cxA = width / 2
      boxes.push(
        <g key={`a${li}`}>
          <line x1={cxA} y1={fromY} x2={cxA} y2={toY - 8} stroke="#94a3b8" strokeWidth={2} />
          <path d={`M ${cxA - 6} ${toY - 14} L ${cxA} ${toY - 2} L ${cxA + 6} ${toY - 14}`}
            fill="none" stroke="#94a3b8" strokeWidth={2} />
        </g>,
      )
    }
    y += layerH + arrowH
  })

  return (
    <div className="overflow-x-auto rounded-lg">
      <svg viewBox={`0 0 ${width} ${totalH}`} style={{ minWidth: 640 }} role="img"
        aria-label="研究架构图">
        {boxes}
      </svg>
    </div>
  )
}

function WaitTimer({ seconds }: { seconds: number }) {
  const [remaining, setRemaining] = useState(seconds)
  const [step, setStep] = useState(0)
  const steps = ['AI 文字分析...', '架构图生成...', '渲染结果...']

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
  const [imgFailed, setImgFailed] = useState<Record<number, boolean>>({})

  if (loading) return <WaitTimer seconds={estimatedTime} />

  // 从全文中提取所有图片 URL
  const imageUrls: string[] = []
  const patterns = [
    /!\[.*?\]\(((?:https?:\/\/|\/)[^)]+)\)/g,                 // markdown 图片（远程或本机）
    /\[.*?\]\(((?:https?:\/\/|\/)[^\)]+\.(png|jpg|jpeg|webp|gif)[^\)]*)\)/gi, // 带后缀链接
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

  // 分离文字分析和架构图（兼容 ## 研究架构图 / 3.研究架构图(文字描述) 等格式）
  const archIndex = analysis.search(/研究架构图/)
  const textPart = archIndex >= 0 ? analysis.slice(0, archIndex) : analysis
  const diagramPart = archIndex >= 0 ? analysis.slice(archIndex) : ''

  return (
    <div className="space-y-4">
      {/* 文字分析 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary-500" />
          {isChinese ? 'AI 文字分析' : 'AI Text Analysis'}
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
              {isChinese ? 'AI 研究架构图' : 'AI Research Architecture'}
            </h3>
            {imgFailed[i] && diagramPart ? (
              <ArchitectureSvg text={diagramPart} />
            ) : imgFailed[i] ? (
              <div className="text-sm text-gray-500">{isChinese ? '图片加载失败' : 'Image failed to load'}</div>
            ) : (
              <>
                <img src={url} alt={isChinese ? '研究架构图' : 'Architecture'}
                  className="w-full rounded-lg shadow-md cursor-pointer hover:shadow-lg transition-shadow"
                  onError={() => setImgFailed((prev) => ({ ...prev, [i]: true }))}
                  onClick={() => window.open(url, '_blank')} />
                <a href={url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline mt-2">
                  {isChinese ? '🔍 查看大图' : '🔍 View full size'}
                </a>
              </>
            )}
          </div>
        ))
      ) : diagramPart && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-purple-500" />
            {isChinese ? 'AI 研究架构图' : 'AI Research Architecture'}
          </h3>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <ArchitectureSvg text={diagramPart} />
          </div>
        </div>
      )}
    </div>
  )
}
