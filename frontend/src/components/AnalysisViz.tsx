/**
 * AI 分析结果可视化组件
 * Provider-neutral text analysis + generic SVG architecture renderer
 *
 * 架构图渲染原则（泛化设计）：
 * - 任何来源的架构文字（## 研究架构图 / 3.研究架构图(文字描述) /
 *   "研究架构图（文字描述）" + 代码块 / 纯分层文本）都会先解析为
 *   通用「层 → 模块」结构，再交给同一个 SVG 布局引擎渲染。
 * - 不依赖 AI 生图模型：每次都是确定性代码生成，结果稳定、可排版。
 */
import { useState, useEffect } from 'react'
import { Clock, Sparkles, FlaskConical, ChevronDown } from 'lucide-react'
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

/**
 * 通用架构解析器：把任意格式的架构文字转成「层 → 模块」结构。
 * 泛化启发式（不针对具体文字）：
 *   1. 清理 markdown 符号（代码围栏 / 标题 # / 列表符号 / 编号 / 加粗 / 反引号）
 *   2. 行类型分流：
 *      - 列表项（- / * / + 开头）→ 一律是模块
 *      - markdown 标题（### 开头）→ 一律是层
 *      - 顶格纯文本 → 含强层词（层/阶段/编码器/Layer/Encoder…）或以冒号结尾 → 层；否则模块
 */
function parseLayers(text: string): { title: string; modules: string[] }[] {
  const lines = text.split('\n').filter((l) => l.trim().length > 0)
  const layers: { title: string; modules: string[] }[] = []
  let current: { title: string; modules: string[] } | null = null

  const isLayerTitle = (clean: string): boolean => {
    if (clean.includes('|') || clean.includes('=')) return false
    if (/(层|阶段|模块组|环节|编码器|解码器|主干|Encoder|Decoder|Layer|Stage|Phase|Block|Pipeline|Controller|Policy|Critic|Reward|Optimizer)/i.test(clean)) return true
    if (/[:：]$/.test(clean)) return true
    // 短命名结构词（≤18 字、不含冒号/顿号/逗号、非内容行）
    if (clean.length <= 18 && !clean.includes(':') && !clean.includes('、') && !clean.includes(',') &&
        /^(输入|输出|特征|表示|决策|应用|优化|训练|推理|融合|多模态|模型|编码|解码|系统|架构|整体|端到端|数据流|信息流|动作|奖励|策略|环境|经验回放|轨迹)/.test(clean)) return true
    return false
  }
  const modName = (clean: string): string =>
    clean.replace(/^(.{2,28}?)[:：].*$/, '$1').trim()

  for (const line of lines) {
    const stripped = line.trim()
    // 代码围栏整行跳过
    if (/^```+/.test(stripped)) continue
    const isList = /^[-*+•]\s+/.test(stripped)
    const isHeading = /^#{1,6}\s+/.test(stripped)
    const clean = stripped
      .replace(/^#{1,6}\s*/g, '')
      .replace(/^[-*+•]\s+/g, '')
      .replace(/^\d+[.、)．:：]\s*/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/`/g, '')
      .trim()
    if (!clean) continue

    if (isList) {
      if (current) current.modules.push(modName(clean))
    } else if (isHeading || isLayerTitle(clean)) {
      current = { title: clean.replace(/[:：]\s*$/, ''), modules: [] }
      layers.push(current)
    } else if (current) {
      current.modules.push(modName(clean))
    }
  }
  return layers.filter((l) => l.title || l.modules.length > 0)
}

/**
 * 通用 SVG 架构图引擎
 * 设计：层 = 渐变泳道（左侧色条 + 左上角层标题 + 右上角序号）；
 *       模块 = 白色圆角卡片（层主色描边 + 微阴影），行内居中排布；
 *       层间 = 虚线箭头流线。每层配色取自 7 色学术色板，自动循环。
 */
function ArchitectureSvg({ text }: { text: string }) {
  // 提取标题行（可选，如 "研究架构图" / "3.研究架构图(文字描述)"）
  let title = ''
  let body = text
  const titleMatch = text.match(/^\s*\d*[.、)．]?\s*(研究架构图[^\n]*)/)
  if (titleMatch && titleMatch[1].length <= 32) {
    title = titleMatch[1].trim().replace(/[:：]$/, '')
    body = text.replace(titleMatch[0], '')
  }
  const cleaned = body.replace(/^```+[a-zA-Z]*\s*$/gm, '').trim()
  const layers = parseLayers(cleaned)

  // 泛化兜底：解析不出结构时也做干净排版（绝不暴露原始 markdown 符号）
  if (layers.length === 0) {
    const safe = cleaned
      .replace(/^#{1,6}\s*/gm, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/`/g, '')
    return (
      <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
        {safe.split('\n').filter(Boolean).map((l, i) => (
          <p key={i} className="pl-3 border-l-2 border-gray-200 dark:border-gray-700 mb-1">
            {l.replace(/^[-*+]\s+/, '• ')}
          </p>
        ))}
      </div>
    )
  }

  // ---- 布局参数 ----
  const width = 840
  const modW = 176
  const modH = 38
  const gap = 14
  const padX = 20
  const padTop = 42
  const padBottom = 14
  const arrowH = 30
  const titleH = title ? 46 : 0
  const cols = Math.max(1, Math.floor((width - padX * 2 + gap) / (modW + gap)))
  const rowH = modH + 10

  const palette = [
    { main: '#2563eb', bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
    { main: '#0891b2', bg: '#ecfeff', border: '#a5f3fc', text: '#155e75' },
    { main: '#059669', bg: '#ecfdf5', border: '#a7f3d0', text: '#065f46' },
    { main: '#d97706', bg: '#fffbeb', border: '#fde68a', text: '#92400e' },
    { main: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe', text: '#5b21b6' },
    { main: '#db2777', bg: '#fdf2f8', border: '#fbcfe8', text: '#9d174d' },
    { main: '#475569', bg: '#f8fafc', border: '#cbd5e1', text: '#334155' },
  ]

  const rowCounts = layers.map((l) => Math.max(1, Math.ceil(Math.min(l.modules.length, 16) / cols)))
  const layerHs = rowCounts.map((rows) => padTop + rows * rowH + padBottom)
  const totalH = titleH + layerHs.reduce((a, b) => a + b, 0) + arrowH * (layers.length - 1) + 16

  let y = titleH + 8
  const els: React.ReactNode[] = []

  if (title) {
    els.push(
      <g key="title">
        <text x={width / 2} y={30} fontSize={17} fontWeight={700} fill="#1f2937" textAnchor="middle">
          {title}
        </text>
        <line x1={width / 2 - 42} y1={38} x2={width / 2 + 42} y2={38} stroke="#e5e7eb" strokeWidth={2} strokeLinecap="round" />
      </g>,
    )
  }

  layers.forEach((layer, li) => {
    const pal = palette[li % palette.length]
    const layerH = layerHs[li]
    const gid = `arch-lg-${li}`
    const n = Math.min(layer.modules.length, 16)

    // 泳道背景（纵向渐变）+ 左侧色条
    els.push(
      <defs key={`defs-${li}`}>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={pal.bg} />
          <stop offset="100%" stopColor={pal.bg} stopOpacity={0.5} />
        </linearGradient>
      </defs>,
      <rect key={`bg-${li}`} x={8} y={y} width={width - 16} height={layerH} rx={14}
        fill={`url(#${gid})`} stroke={pal.border} strokeWidth={1.2} />,
      <rect key={`bar-${li}`} x={8} y={y + 14} width={5} height={layerH - 28} rx={2.5} fill={pal.main} />,
      // 层标题 + 序号
      <text key={`lt-${li}`} x={26} y={y + 26} fontSize={14.5} fontWeight={700} fill={pal.text}>
        {layer.title.length > 30 ? layer.title.slice(0, 29) + '…' : layer.title}
      </text>,
      <text key={`li-${li}`} x={width - 30} y={y + 26} fontSize={11} fill="#9ca3af" textAnchor="end" fontWeight={500}>
        {li + 1} / {layers.length}
      </text>,
    )

    // 模块卡片（行内居中）
    layer.modules.slice(0, 16).forEach((mod, mi) => {
      const row = Math.floor(mi / cols)
      const rowStart = row * cols
      const inRow = Math.min(cols, n - rowStart)
      const rowTotalW = inRow * modW + (inRow - 1) * gap
      const startX = padX + (width - padX * 2 - rowTotalW) / 2
      const col = mi - rowStart
      const mx = startX + col * (modW + gap)
      const my = y + padTop + row * rowH
      const label = mod.length > 20 ? mod.slice(0, 19) + '…' : mod
      els.push(
        <g key={`m-${li}-${mi}`}>
          <rect x={mx} y={my} width={modW} height={modH} rx={9}
            fill="#ffffff" stroke={pal.border} strokeWidth={1.4}
            filter="url(#arch-shadow)" />
          <rect x={mx} y={my} width={4} height={modH} rx={2} fill={pal.main} opacity={0.55} />
          <text x={mx + modW / 2 + 4} y={my + modH / 2 + 4.5}
            fontSize={12} fill="#374151" textAnchor="middle" fontWeight={500}>
            {label}
          </text>
        </g>,
      )
    })

    // 层间虚线箭头
    if (li < layers.length - 1) {
      const fromY = y + layerH
      const toY = fromY + arrowH
      const cx = width / 2
      els.push(
        <g key={`a-${li}`}>
          <line x1={cx} y1={fromY} x2={cx} y2={toY - 10} stroke="#94a3b8" strokeWidth={2} strokeDasharray="4 3" />
          <path d={`M ${cx - 7} ${toY - 17} L ${cx} ${toY - 3} L ${cx + 7} ${toY - 17}`} fill="none" stroke="#94a3b8" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        </g>,
      )
    }
    y += layerH + arrowH
  })

  return (
    <div className="overflow-x-auto rounded-lg">
      <svg viewBox={`0 0 ${width} ${totalH}`} style={{ minWidth: 720, maxWidth: '100%' }} role="img"
        aria-label="研究架构图" className="w-full h-auto">
        <defs>
          <filter id="arch-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="1.5" stdDeviation="2" floodColor="#00000018" />
          </filter>
        </defs>
        {els}
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

  // 分离文字分析和架构图（兼容多种格式）
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

      {/* 架构图：通用 SVG 引擎（每次确定性生成，不依赖 AI 生图） */}
      {diagramPart ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-purple-500" />
            {isChinese ? 'AI 研究架构图' : 'AI Research Architecture'}
            <span className="ml-auto text-[11px] font-normal text-gray-400">
              {isChinese ? 'SVG 渲染' : 'SVG rendered'}
            </span>
          </h3>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-3">
            <ArchitectureSvg text={diagramPart} />
          </div>
          {imageUrls.length > 0 && (
            <details className="mt-3">
              <summary className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline cursor-pointer select-none">
                <ChevronDown className="w-3.5 h-3.5" />
                {isChinese ? 'AI 绘制版大图' : 'AI-drawn version'}
              </summary>
              <div className="mt-2 space-y-3">
                {imageUrls.map((url, i) => (
                  <img key={i} src={url} alt={isChinese ? 'AI 绘制架构图' : 'AI-drawn architecture'}
                    className="w-full rounded-lg border border-gray-200 dark:border-gray-700" />
                ))}
              </div>
            </details>
          )}
        </div>
      ) : imageUrls.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-purple-500" />
            {isChinese ? 'AI 研究架构图' : 'AI Research Architecture'}
          </h3>
          {imageUrls.map((url, i) => (
            <img key={i} src={url} alt={isChinese ? 'AI 绘制架构图' : 'AI-drawn architecture'}
              className="w-full rounded-lg shadow-md cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => window.open(url, '_blank')} />
          ))}
        </div>
      ) : null}
    </div>
  )
}
