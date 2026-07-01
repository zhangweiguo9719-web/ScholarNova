import { ExternalLink, Quote, Calendar, BookOpen } from 'lucide-react'
import clsx from 'clsx'
import type { Paper } from '@/api/types'
import { useLocaleStore } from '@/stores/localeStore'
import './ResultsList.css'

const sourceLabels: Record<string, string> = {
  semantic_scholar: 'S2',
  openalex: 'OA',
  crossref: 'CR',
  arxiv: 'arXiv',
}

const sourceColors: Record<string, string> = {
  semantic_scholar: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
  openalex: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
  crossref: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
  arxiv: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
}

const impactLabels = {
  highly_cited: { zh: '高被引', en: 'Highly cited' },
  well_cited: { zh: '引用表现优秀', en: 'Well cited' },
  established: { zh: '引用表现稳定', en: 'Established' },
  emerging: { zh: '新近成果', en: 'Emerging' },
  limited_signal: { zh: '引用信号有限', en: 'Limited signal' },
}

interface PaperCardProps {
  paper: Paper
  isSelected?: boolean
  onClick?: (paper: Paper) => void
}

export default function PaperCard({ paper, isSelected = false, onClick }: PaperCardProps) {
  const { locale } = useLocaleStore()
  const isZh = locale === 'zh'

  return (
    <div
      className={clsx('paper-card animate-slide-up', isSelected && 'paper-card-selected')}
      onClick={() => onClick?.(paper)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.(paper) } }}
    >
      {/* Title */}
      <div className="paper-card-header">
        <h3 className="paper-card-title">
          {paper.url ? (
            <a href={paper.url} target="_blank" rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="hover:text-primary-600 dark:hover:text-primary-400">
              {paper.title}
              <ExternalLink className="inline w-3.5 h-3.5 ml-1 opacity-50" />
            </a>
          ) : paper.title}
        </h3>
      </div>

      {/* Authors */}
      {paper.authors.length > 0 && (
        <div className="paper-card-meta">
          <span className="text-gray-600 dark:text-gray-400">
            {paper.authors.slice(0, 3).join(', ')}
            {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
          </span>
        </div>
      )}

      {/* 时间 + 期刊（突出显示） */}
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
        {paper.year && (
          <span className="inline-flex items-center gap-1 font-medium text-gray-700 dark:text-gray-300">
            <Calendar className="w-3 h-3" />
            {paper.year}
          </span>
        )}
        {paper.venue && (
          <span className="inline-flex items-center gap-1 truncate max-w-[280px]">
            <BookOpen className="w-3 h-3 flex-shrink-0" />
            {paper.venue}
          </span>
        )}
      </div>

      {/* Abstract */}
      {paper.abstract && (
        <p className="paper-card-abstract">{paper.abstract}</p>
      )}

      {paper.quality && (
        <div className="paper-quality-strip" title={isZh
          ? '引用百分位按本次候选结果集计算；JCR/中科院分区仅展示已授权核验数据'
          : 'Citation percentile is calculated within this result set; quartiles require verified licensed data'}>
          <span className="paper-quality-score">
            {isZh ? '质量' : 'Quality'} {Math.round(paper.quality.quality_score * 100)}
          </span>
          <span>
            {impactLabels[paper.quality.impact_label]?.[isZh ? 'zh' : 'en']
              ?? paper.quality.impact_label}
          </span>
          <span>
            {isZh ? '引用百分位' : 'Citation percentile'} {Math.round(paper.quality.citation_percentile * 100)}%
          </span>
          <span>
            {isZh ? '年均引用' : 'Citations/year'} {paper.quality.citation_velocity.toFixed(1)}
          </span>
          {paper.quality.jcr_quartile && <span>JCR {paper.quality.jcr_quartile}</span>}
          {paper.quality.cas_quartile && (
            <span>{isZh ? '中科院' : 'CAS'} {paper.quality.cas_quartile}</span>
          )}
          {!paper.quality.jcr_quartile && !paper.quality.cas_quartile && (
            <span className="paper-quality-unverified">
              {isZh ? '分区待授权核验' : 'Quartile unverified'}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="paper-card-footer">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('badge', sourceColors[paper.source] || 'bg-gray-100 text-gray-700')}>
            {sourceLabels[paper.source] || paper.source}
          </span>
          {paper.is_open_access && (
            <span className="badge badge-oa">{isZh ? '开放获取' : 'Open Access'}</span>
          )}
          {paper.relevance_score != null && (
            <span className={clsx(
              'badge',
              paper.relevance_score >= 0.7
                ? 'bg-emerald-50 dark:bg-emerald-900/25 text-emerald-700 dark:text-emerald-300'
                : paper.relevance_score >= 0.45
                  ? 'bg-amber-50 dark:bg-amber-900/25 text-amber-700 dark:text-amber-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
            )}>
              {paper.relevance_score >= 0.7
                ? (isZh ? '高度相关' : 'High relevance')
                : paper.relevance_score >= 0.45
                  ? (isZh ? '部分相关' : 'Partial relevance')
                  : (isZh ? '探索结果' : 'Exploratory')}
            </span>
          )}
          <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
            <Quote className="w-3 h-3" />
            {paper.citation_count.toLocaleString()}
          </span>
        </div>

        {/* 相关度 */}
        {paper.relevance_score != null && (
          <div className="flex items-center gap-1.5" title={isZh ? '与查询的相关度' : 'Relevance to query'}>
            <span className="text-[10px] text-gray-400 dark:text-gray-500">
              {isZh ? '相关度' : 'Relevance'}
            </span>
            <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${Math.round(paper.relevance_score * 100)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-primary-600 dark:text-primary-400">
              {Math.round(paper.relevance_score * 100)}%
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
