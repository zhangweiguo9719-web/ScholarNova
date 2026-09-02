/** 搜索页临时状态：只在当前页面会话内保留，不写入浏览器存储。 */
import { create } from 'zustand'
import type { SearchRunDetail, PaperDetail, AnalysisResult, EvidenceSpan } from '@/api/types'

interface SearchState {
  searchRun: SearchRunDetail | null
  isLoading: boolean
  error: string | null
  query: string
  selectedPaper: PaperDetail | null
  analysis: AnalysisResult | null
  analysisLoading: boolean
  evidenceSpans: EvidenceSpan[]
  evidenceLoading: boolean

  setSearchRun: (run: SearchRunDetail | null) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setQuery: (query: string) => void
  setSelectedPaper: (paper: PaperDetail | null) => void
  setAnalysis: (analysis: AnalysisResult | null) => void
  setAnalysisLoading: (loading: boolean) => void
  setEvidenceSpans: (spans: EvidenceSpan[]) => void
  setEvidenceLoading: (loading: boolean) => void
  clearSearch: () => void
  clearDetail: () => void
}

export const useSearchStore = create<SearchState>()((set) => ({
      searchRun: null, isLoading: false, error: null, query: '',
      selectedPaper: null, analysis: null, analysisLoading: false,
      evidenceSpans: [], evidenceLoading: false,

      setSearchRun: (searchRun) => set({ searchRun }),
      setIsLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setQuery: (query) => set({ query }),
      setSelectedPaper: (selectedPaper) => set({ selectedPaper }),
      setAnalysis: (analysis) => set({ analysis }),
      setAnalysisLoading: (analysisLoading) => set({ analysisLoading }),
      setEvidenceSpans: (evidenceSpans) => set({ evidenceSpans }),
      setEvidenceLoading: (evidenceLoading) => set({ evidenceLoading }),

      clearSearch: () => set({
        searchRun: null, isLoading: false, error: null, query: '',
        selectedPaper: null, analysis: null, analysisLoading: false,
        evidenceSpans: [], evidenceLoading: false,
      }),
      clearDetail: () => set({
        selectedPaper: null, analysis: null, evidenceSpans: [],
      }),
    }))
