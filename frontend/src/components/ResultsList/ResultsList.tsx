import { useState, useMemo } from 'react'
import { FileSearch, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import clsx from 'clsx'
import type { Paper } from '@/api/types'
import { useLocaleStore } from '@/stores/localeStore'
import PaperCard from './PaperCard'
import './ResultsList.css'

type SortKey = 'relevance' | 'year' | 'citations'

interface ResultsListProps {
  papers: Paper[]
  selectedPaperId?: string | null
  onPaperClick?: (paper: Paper) => void
}

export default function ResultsList({ papers, selectedPaperId, onPaperClick }: ResultsListProps) {
  const { locale } = useLocaleStore()
  const isZh = locale === 'zh'
  const [sortKey, setSortKey] = useState<SortKey>('relevance')
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc')

  const sortedPapers = useMemo(() => {
    const arr = [...papers]
    arr.sort((a, b) => {
      let cmp = 0
      if (sortKey === 'year') cmp = (a.year || 0) - (b.year || 0)
      else if (sortKey === 'citations') cmp = a.citation_count - b.citation_count
      else cmp = (a.relevance_score || 0) - (b.relevance_score || 0)
      return sortDir === 'desc' ? -cmp : cmp
    })
    return arr
  }, [papers, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button onClick={() => toggleSort(k)}
      className={clsx('inline-flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium transition-colors',
        sortKey === k ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300'
          : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800')}>
      {sortKey === k ? (sortDir === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3" />}
      {label}
    </button>
  )

  if (papers.length === 0) {
    return (
      <div className="results-empty">
        <FileSearch className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
        <p className="text-gray-500 dark:text-gray-400 font-medium">
          {isZh ? '未找到论文' : 'No papers found'}
        </p>
        <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
          {isZh ? '尝试换一个搜索关键词' : 'Try a different search query'}
        </p>
      </div>
    )
  }

  return (
    <div className="results-list">
      <div className="results-list-header">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {papers.length} {isZh ? '篇论文' : 'results'}
        </span>
        <div className="flex items-center gap-1">
          <SortBtn k="relevance" label={isZh ? '相关度' : 'Relevance'} />
          <SortBtn k="year" label={isZh ? '年份' : 'Year'} />
          <SortBtn k="citations" label={isZh ? '引用' : 'Citations'} />
        </div>
      </div>
      <div className="results-list-body custom-scrollbar">
        {sortedPapers.map((paper, index) => (
          <PaperCard
            key={paper.id}
            paper={paper}
            isSelected={paper.id === selectedPaperId}
            onClick={onPaperClick}
            autoEnrich={index < 8}
          />
        ))}
      </div>
    </div>
  )
}
