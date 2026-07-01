/**
 * 搜索状态管理 - 持久化搜索结果 + 搜索历史
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SearchRunDetail, PaperDetail, AnalysisResult, EvidenceSpan } from '@/api/types'

export interface SearchHistoryItem {
  query: string
  timestamp: number
  resultCount: number
}

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
  history: SearchHistoryItem[]

  setSearchRun: (run: SearchRunDetail | null) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setQuery: (query: string) => void
  setSelectedPaper: (paper: PaperDetail | null) => void
  setAnalysis: (analysis: AnalysisResult | null) => void
  setAnalysisLoading: (loading: boolean) => void
  setEvidenceSpans: (spans: EvidenceSpan[]) => void
  setEvidenceLoading: (loading: boolean) => void
  addToHistory: (query: string, resultCount: number) => void
  removeFromHistory: (query: string) => void
  clearHistory: () => void
  clearSearch: () => void
  clearDetail: () => void
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      searchRun: null, isLoading: false, error: null, query: '',
      selectedPaper: null, analysis: null, analysisLoading: false,
      evidenceSpans: [], evidenceLoading: false,
      history: [],

      setSearchRun: (searchRun) => set({ searchRun }),
      setIsLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setQuery: (query) => set({ query }),
      setSelectedPaper: (selectedPaper) => set({ selectedPaper }),
      setAnalysis: (analysis) => set({ analysis }),
      setAnalysisLoading: (analysisLoading) => set({ analysisLoading }),
      setEvidenceSpans: (evidenceSpans) => set({ evidenceSpans }),
      setEvidenceLoading: (evidenceLoading) => set({ evidenceLoading }),

      addToHistory: (query, resultCount) => {
        const existing = get().history
        const filtered = existing.filter((h) => h.query !== query)
        const newHistory = [
          { query, timestamp: Date.now(), resultCount },
          ...filtered,
        ].slice(0, 20) // 最多保留20条
        set({ history: newHistory })
      },

      removeFromHistory: (query) => {
        set({ history: get().history.filter((h) => h.query !== query) })
      },

      clearHistory: () => set({ history: [] }),

      clearSearch: () => set({
        searchRun: null, isLoading: false, error: null,
        selectedPaper: null, analysis: null, evidenceSpans: [],
      }),
      clearDetail: () => set({
        selectedPaper: null, analysis: null, evidenceSpans: [],
      }),
    }),
    {
      name: 'scholar-search-state',
      partialize: (s) => ({
        searchRun: s.searchRun,
        query: s.query,
        history: s.history,
      }),
    }
  )
)
