import { useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Loader2, Search as SearchIcon, AlertCircle, BookOpen } from 'lucide-react'
import clsx from 'clsx'
import { searchApi, papersApi } from '@/api/client'
import { useSearchStore } from '@/stores/searchStore'
import { useLocaleStore } from '@/stores/localeStore'
import SearchBar from '@/components/SearchBar/SearchBar'
import QueryPlan from '@/components/QueryPlan/QueryPlan'
import SearchInsights from '@/components/SearchInsights/SearchInsights'
import ResultsList from '@/components/ResultsList/ResultsList'
import PaperDetailPanel from '@/components/PaperDetail/PaperDetail'
import { PaperCardSkeleton } from '@/components/Skeleton'
import toast from 'react-hot-toast'

export default function Search() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryParam = searchParams.get('q') || ''
  const { t, locale } = useLocaleStore()

  const {
    searchRun, isLoading, error, query, history,
    selectedPaper, analysis, analysisLoading, evidenceSpans, evidenceLoading,
    setSearchRun, setIsLoading, setError, setQuery,
    setSelectedPaper, setAnalysis, setAnalysisLoading,
    setEvidenceSpans, addToHistory,
  } = useSearchStore()

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastStartedQueryRef = useRef<string | null>(null)

  useEffect(() => {
    return () => { if (pollTimerRef.current) clearTimeout(pollTimerRef.current) }
  }, [])

  // 搜索 query 变化时执行搜索
  useEffect(() => {
    if (queryParam) {
      // 如果 URL 有查询且 store 里没有对应结果，执行搜索
      if ((queryParam !== query || !searchRun) && lastStartedQueryRef.current !== queryParam) {
        lastStartedQueryRef.current = queryParam
        setQuery(queryParam)
        performSearch(queryParam)
      }
    }
    // 不清空搜索状态——切换页面回来时保留结果
  }, [queryParam])

  const performSearch = async (searchQuery: string) => {
    lastStartedQueryRef.current = searchQuery
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    setIsLoading(true)
    setError(null)
    setSearchRun(null)
    setSelectedPaper(null)
    setAnalysis(null)
    setEvidenceSpans([])

    try {
      const response = await searchApi.create({ query: searchQuery })
      pollSearchStatus(response.data.run_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || (t('common.error') + '. ' + t('common.retry')))
      setIsLoading(false)
    }
  }

  const pollSearchStatus = (runId: string) => {
    let attempts = 0
    const poll = async () => {
      try {
        const response = await searchApi.getRun(runId)
        setSearchRun(response.data)
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setIsLoading(false)
          if (response.data.status === 'completed') {
            addToHistory(response.data.original_query, response.data.results?.length || 0)
          } else {
            setError('搜索失败，请换个关键词试试')
          }
          return
        }
        attempts++
        if (attempts < 150) pollTimerRef.current = setTimeout(poll, 2000)
        else { setError('搜索超时'); setIsLoading(false) }
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取搜索状态失败')
        setIsLoading(false)
      }
    }
    poll()
  }

  const handleSearch = (newQuery: string) => {
    navigate(`/search?q=${encodeURIComponent(newQuery)}`, { replace: true })
  }

  const handlePaperClick = useCallback(async (paper: any) => {
    setAnalysis(null)
    setEvidenceSpans([])
    try {
      const response = await papersApi.get(paper.id)
      setSelectedPaper(response.data)
    } catch {
      setSelectedPaper({
        ...paper, references: [], citations: [], fields_of_study: [],
        keywords: [], publication_date: null, volume: null, issue: null, pages: null,
      })
    }
  }, [searchRun?.run_id])

  const handleAnalyze = useCallback(async (customQuery?: string) => {
    if (!selectedPaper) return
    setAnalysisLoading(true)
    try {
      const response = await papersApi.analyze(selectedPaper.id, {
        query: customQuery || query || t('search.placeholder'),
        analysis_type: 'full',
      })
      setAnalysis(response.data)
    } catch {
      toast.error(t('common.error') + '. ' + t('common.retry'))
    } finally { setAnalysisLoading(false) }
  }, [selectedPaper, query])

  const handleCloseDetail = () => { setSelectedPaper(null); setAnalysis(null); setEvidenceSpans([]) }

  const progress = searchRun?.progress
  const progressPercent = progress
    ? Math.round((progress.completed_sources / Math.max(progress.total_sources, 1)) * 100)
    : 0

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
        <div className="max-w-4xl mx-auto">
          <SearchBar defaultValue={queryParam || query} size="sm" loading={isLoading} onSubmit={handleSearch} />
        </div>
      </div>

      {isLoading && (
        <div className="h-1 bg-gray-100 dark:bg-gray-800">
          <div className="progress-bar" style={{ width: `${progressPercent}%` }} />
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="max-w-4xl mx-auto px-4 py-4">
            {error && (
              <div className="flex items-start gap-3 p-4 mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg animate-fade-in">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
                  <button onClick={() => queryParam && performSearch(queryParam)}
                    className="text-xs text-red-600 dark:text-red-400 hover:underline mt-1">{t('common.retry')}</button>
                </div>
              </div>
            )}

            {isLoading && !searchRun && (
              <div className="space-y-3">{[1, 2, 3].map((i) => <PaperCardSkeleton key={i} />)}</div>
            )}

            {isLoading && searchRun && (
              <div className="p-3 mb-4 bg-primary-50 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-800 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary-600 dark:text-primary-400" />
                  <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                    {progress?.current_phase === 'searching' ? '正在检索...' :
                     progress?.current_phase === 'deduplicating' ? '去重处理...' :
                     progress?.current_phase === 'ranking' ? '排序中...' :
                     '规划中...'}
                  </span>
                </div>
                {/* 数据源状态 */}
                {progress && progress.total_sources > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {Array.from({ length: progress.total_sources }).map((_, i) => (
                      <span key={i} className={clsx(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs',
                        i < progress.completed_sources
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
                      )}>
                        {i < progress.completed_sources ? '✅' : '⏳'}
                        {i < progress.completed_sources ? `${progress.deduplicated_papers} 篇` : `源${i + 1}`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {searchRun?.query_plan && (
              <QueryPlan plan={searchRun.query_plan} originalQuery={searchRun.original_query} />
            )}

            {searchRun?.status === 'completed' && (
              <SearchInsights run={searchRun} />
            )}

            {/* 搜索结果 */}
            {searchRun && (!isLoading || searchRun.results.length > 0) && (
              <div className="mt-4">
                <ResultsList papers={searchRun.results} selectedPaperId={selectedPaper?.id} onPaperClick={handlePaperClick} />
              </div>
            )}

            {/* 没有 URL 查询时：显示空状态 + 搜索历史 */}
            {!queryParam && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <BookOpen className="w-16 h-16 text-gray-200 dark:text-gray-700 mb-4" />
                <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                  {locale === 'zh' ? '开始你的研究' : 'Start your research'}
                </h3>
                <p className="text-sm text-gray-400 dark:text-gray-500 max-w-sm mb-6">
                  {locale === 'zh'
                    ? '输入研究问题或主题，AI 会规划优化的子查询并搜索多个学术数据库'
                    : 'Enter a research question or topic above. The AI will plan optimized sub-queries and search across multiple academic databases.'}
                </p>

                {/* 搜索历史 */}
                {history.length > 0 && (
                  <div className="w-full max-w-md">
                    <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                      {locale === 'zh' ? '📚 搜索历史' : '📚 Search History'}
                    </h4>
                    <div className="space-y-1">
                      {history.slice(0, 10).map((item, i) => (
                        <button
                          key={i}
                          onClick={() => handleSearch(item.query)}
                          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left
                            bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800
                            transition-colors group"
                        >
                          <SearchIcon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 truncate">
                            {item.query}
                          </span>
                          <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
                            {item.resultCount} {locale === 'zh' ? '篇' : 'papers'}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!isLoading && searchRun?.status === 'completed' && searchRun.results.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <SearchIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-gray-500 dark:text-gray-400 font-medium">{t('search.noResults')}</p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{t('search.noResultsDesc')}</p>
              </div>
            )}
          </div>
        </div>

        {selectedPaper && (
          <div className="w-full md:w-[400px] lg:w-[440px] flex-shrink-0 overflow-hidden">
            <PaperDetailPanel
              paper={selectedPaper} analysis={analysis} analysisLoading={analysisLoading}
              evidenceSpans={evidenceSpans} evidenceLoading={evidenceLoading}
              runId={searchRun?.run_id ?? null} onClose={handleCloseDetail} onAnalyze={handleAnalyze}
            />
          </div>
        )}
      </div>
    </div>
  )
}
