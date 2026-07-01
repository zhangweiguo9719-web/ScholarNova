import { useState } from 'react'
import {
  X, ExternalLink, Copy, Check, Loader2, Sparkles, BookOpen,
  Calendar, Hash, Users, Lightbulb, AlertTriangle, FlaskConical,
  Languages, BookMarked,
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useLocaleStore } from '@/stores/localeStore'
import { knowledgeApi } from '@/api/client'
import type { PaperDetail as PaperDetailType, AnalysisResult } from '@/api/types'
import KnowledgeForm from '@/components/KnowledgeForm/KnowledgeForm'
import './PaperDetail.css'

interface PaperDetailProps {
  paper: PaperDetailType
  analysis: AnalysisResult | null
  analysisLoading: boolean
  evidenceSpans: import('@/api/types').EvidenceSpan[]
  evidenceLoading: boolean
  runId?: string | null
  onClose: () => void
  onAnalyze: (query?: string) => void
}

type AnalysisKey = 'full' | 'research_points' | 'limitations' | 'methodology'

const analysisConfig: Record<AnalysisKey, { icon: any; zhLabel: string; enLabel: string; query: string }> = {
  full: { icon: Sparkles, zhLabel: '全面分析', enLabel: 'Full Analysis', query: '请对这篇论文进行全面深度分析，包括：1)核心研究问题 2)创新点和主要贡献 3)研究方法和技术路线 4)实验设计和结果 5)论文优点和局限性 6)与当前研究方向的关联。请用中文回答。' },
  research_points: { icon: Lightbulb, zhLabel: '研究点提炼', enLabel: 'Research Points', query: '请提炼这篇论文的核心研究点，包括：1)研究问题是什么 2)提出了什么新方法/新理论 3)核心创新点（与已有方法的区别） 4)主要贡献（对领域的推动）。请用中文详细回答。' },
  limitations: { icon: AlertTriangle, zhLabel: '研究缺陷', enLabel: 'Limitations', query: '请分析这篇论文的研究缺陷和局限性，包括：1)方法的假设和限制条件 2)实验设计的不足 3)数据集的局限 4)未讨论的潜在问题 5)未来可改进的方向。请用中文详细回答。' },
  methodology: { icon: FlaskConical, zhLabel: '方法论拆解', enLabel: 'Methodology', query: '请拆解这篇论文的研究方法，包括：1)整体技术路线 2)核心算法/模型架构 3)实验设计（数据集、基线、评估指标） 4)关键实现细节 5)方法的可复现性评估。请用中文详细回答。' },
}

export default function PaperDetailPanel({
  paper, analysis, analysisLoading,
  onClose, onAnalyze,
}: PaperDetailProps) {
  const { locale } = useLocaleStore()
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'abstract' | 'analysis' | 'evidence'>('abstract')
  const [translatedAbstract, setTranslatedAbstract] = useState<string | null>(null)
  const [translating, setTranslating] = useState(false)
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisKey | null>(null)
  const [knowledgeFormOpen, setKnowledgeFormOpen] = useState(false)
  const [knowledgeCategories, setKnowledgeCategories] = useState<{ name: string; count: number }[]>([])

  const isChinese = locale === 'zh'

  const handleTranslate = async () => {
    if (translatedAbstract) { setTranslatedAbstract(null); return }
    setTranslating(true)
    try {
      const res = await fetch('/api/v1/papers/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: paper.abstract || paper.title, target_lang: 'zh' }),
      })
      if (res.ok) { const data = await res.json(); setTranslatedAbstract(data.translated) }
      else toast.error(isChinese ? '翻译失败' : 'Translation failed')
    } catch { toast.error(isChinese ? '翻译失败' : 'Translation failed') }
    finally { setTranslating(false) }
  }

  const handleAnalysisClick = (key: AnalysisKey) => {
    setActiveAnalysis(key)
    setActiveTab('analysis')
    onAnalyze(analysisConfig[key].query)
  }

  const handleSaveToKnowledge = async () => {
    try {
      const response = await knowledgeApi.getCategories()
      setKnowledgeCategories(response.data)
    } catch {
      setKnowledgeCategories([])
    }
    setKnowledgeFormOpen(true)
  }

  const copyToClipboard = async (text: string, field: string) => {
    try { await navigator.clipboard.writeText(text); setCopiedField(field); toast.success(isChinese ? '已复制' : 'Copied'); setTimeout(() => setCopiedField(null), 2000) }
    catch { toast.error(isChinese ? '复制失败' : 'Failed to copy') }
  }

  const formats = {
    apa: `${paper.authors.join(', ')}${paper.year ? ` (${paper.year}).` : '.'} ${paper.title}.${paper.venue ? ` *${paper.venue}*.` : ''}${paper.doi ? ` https://doi.org/${paper.doi}` : ''}`,
    bibtex: `@article{${paper.id},\n  title={${paper.title}},\n  author={${paper.authors.join(' and ')}},\n${paper.year ? `  year={${paper.year}},\n` : ''}${paper.venue ? `  journal={${paper.venue}},\n` : ''}${paper.doi ? `  doi={${paper.doi}},\n` : ''}}`,
  }

  // 解析分析结果为结构化段落
  const renderAnalysis = (text: string) => {
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
    <div className="paper-detail animate-fade-in">
      {/* Header */}
      <div className="paper-detail-header">
        <div className="flex-1 min-w-0">
          <h2 className="paper-detail-title">{paper.title}</h2>
        </div>
        <button onClick={onClose} className="paper-detail-close"><X className="w-5 h-5" /></button>
      </div>

      {/* Meta */}
      <div className="paper-detail-meta">
        {paper.authors.length > 0 && <div className="meta-row"><Users className="w-4 h-4" /><span>{paper.authors.join(', ')}</span></div>}
        {paper.year && <div className="meta-row"><Calendar className="w-4 h-4" /><span>{paper.year}</span></div>}
        {paper.venue && <div className="meta-row"><BookOpen className="w-4 h-4" /><span>{paper.venue}</span></div>}
        {paper.doi && <div className="meta-row"><Hash className="w-4 h-4" /><a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">{paper.doi}</a></div>}
      </div>

      {/* Links */}
      <div className="paper-detail-links">
        {paper.url && <a href={paper.url} target="_blank" rel="noopener noreferrer" className="paper-link"><ExternalLink className="w-3.5 h-3.5" />{isChinese ? '查看原文' : 'View Paper'}</a>}
        {paper.pdf_url && <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="paper-link paper-link-oa"><ExternalLink className="w-3.5 h-3.5" />PDF</a>}
      </div>

      {/* Analysis buttons */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">🤖 {isChinese ? 'AI 深度分析' : 'AI Deep Analysis'}</p>
        <div className="flex flex-wrap gap-1.5">
          {(Object.entries(analysisConfig) as [AnalysisKey, typeof analysisConfig[AnalysisKey]][]).map(([key, { icon: Icon, zhLabel, enLabel }]) => (
            <button key={key} onClick={() => handleAnalysisClick(key)} disabled={analysisLoading}
              className={clsx('inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all',
                activeAnalysis === key ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700',
                analysisLoading && 'opacity-50 cursor-not-allowed')}>
              {analysisLoading && activeAnalysis === key
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <Icon className="w-3 h-3" />}
              {isChinese ? zhLabel : enLabel}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="paper-detail-tabs">
        {(['abstract', 'analysis'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={clsx('paper-tab', activeTab === tab && 'paper-tab-active')}>
            {tab === 'abstract' && <BookOpen className="w-3.5 h-3.5" />}
            {tab === 'analysis' && <Sparkles className="w-3.5 h-3.5" />}
            {tab === 'abstract' ? (isChinese ? '摘要' : 'Abstract') : (isChinese ? '分析' : 'Analysis')}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="paper-detail-content custom-scrollbar">
        {activeTab === 'abstract' && (
          <div className="animate-fade-in">
            {paper.abstract && (
              <button onClick={handleTranslate} disabled={translating}
                className="inline-flex items-center gap-1 px-2.5 py-1 mb-3 rounded-md text-xs font-medium bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors">
                {translating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Languages className="w-3 h-3" />}
                {translatedAbstract ? (isChinese ? '显示原文' : 'Show Original') : (isChinese ? '翻译为中文' : 'Translate to Chinese')}
              </button>
            )}
            {translatedAbstract
              ? <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">{translatedAbstract}</p>
              : paper.abstract
                ? <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">{paper.abstract}</p>
                : <p className="text-sm text-gray-400 dark:text-gray-500 italic">{isChinese ? '暂无摘要' : 'No abstract available'}</p>
            }
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">{isChinese ? '引用格式' : 'Citation'}</h4>
              <div className="space-y-2">
                {Object.entries(formats).map(([fmt, text]) => (
                  <div key={fmt} className="citation-block">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{fmt}</span>
                      <button onClick={() => copyToClipboard(text, fmt)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                        {copiedField === fmt ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-all font-mono">{text}</pre>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="animate-fade-in">
            {analysisLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                <span className="ml-2 text-sm text-gray-500">{isChinese ? `正在分析：${activeAnalysis ? analysisConfig[activeAnalysis].zhLabel : ''}...` : 'Analyzing...'}</span>
              </div>
            )}
            {!analysis && !analysisLoading && (
              <div className="text-center py-6">
                <Sparkles className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">{isChinese ? '点击上方分析按钮开始' : 'Click a button above to start'}</p>
              </div>
            )}
            {analysis && !analysisLoading && (
              <div>
                {/* 当前分析类型标题 */}
                {activeAnalysis && (
                  <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-200 dark:border-gray-700">
                    {(() => { const cfg = analysisConfig[activeAnalysis]; const Icon = cfg.icon; return <><Icon className="w-4 h-4 text-primary-500" /><h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">{isChinese ? cfg.zhLabel : cfg.enLabel}</h3></> })()}
                  </div>
                )}
                {/* 分析内容 - 结构化展示 */}
                <div className="space-y-1">
                  {renderAnalysis(analysis.summary)}
                </div>
                {/* 方法论 */}
                {analysis.methodology && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-1">{isChinese ? '方法论' : 'Methodology'}</h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.methodology}</p>
                  </div>
                )}
                {/* 关键发现 */}
                {analysis.key_findings.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-1">{isChinese ? '关键发现' : 'Key Findings'}</h4>
                    <ul className="space-y-1">
                      {analysis.key_findings.map((f, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-sm text-gray-700 dark:text-gray-300">
                          <span className="text-primary-500 mt-0.5">•</span>{f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* 优缺点 */}
                <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                  {analysis.strengths.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-green-600 dark:text-green-400 uppercase mb-1">{isChinese ? '✅ 优点' : '✅ Strengths'}</h4>
                      <ul className="space-y-1">
                        {analysis.strengths.map((s, i) => <li key={i} className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">• {s}</li>)}
                      </ul>
                    </div>
                  )}
                  {analysis.weaknesses.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-red-600 dark:text-red-400 uppercase mb-1">{isChinese ? '⚠️ 局限性' : '⚠️ Weaknesses'}</h4>
                      <ul className="space-y-1">
                        {analysis.weaknesses.map((w, i) => <li key={i} className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">• {w}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
                {/* 与查询关联 */}
                {analysis.relevance_to_query && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-1">{isChinese ? '🔗 与查询的关联' : '🔗 Relevance'}</h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.relevance_to_query}</p>
                  </div>
                )}
                {/* Save to Knowledge Button */}
                <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={handleSaveToKnowledge}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/50 border border-primary-200 dark:border-primary-800 transition-colors"
                  >
                    <BookMarked className="w-4 h-4" />
                    {isChinese ? '保存到知识库' : 'Save to Knowledge Base'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Knowledge Form for saving analysis */}
      <KnowledgeForm
        open={knowledgeFormOpen}
        editingItem={null}
        prefill={{
          title: paper.title,
          category: '',
          content: analysis?.summary || '',
          source_paper_id: paper.id,
          source_paper_title: paper.title,
          source_paper_doi: paper.doi,
          research_points: analysis?.key_findings || [],
          tags: paper.keywords?.slice(0, 5) || [],
          notes: null,
        }}
        categories={knowledgeCategories}
        onClose={() => setKnowledgeFormOpen(false)}
        onSuccess={() => {
          setKnowledgeFormOpen(false)
          toast.success(isChinese ? '已保存到知识库' : 'Saved to knowledge base')
        }}
      />
    </div>
  )
}
