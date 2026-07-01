/**
 * 知识库状态管理
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { KnowledgeItem, ResearchRoute } from '@/api/types'

interface KnowledgeState {
  // 知识列表
  items: KnowledgeItem[]
  total: number
  categories: { name: string; count: number }[]
  selectedCategory: string | null
  searchQuery: string

  // 选中的知识条目
  selectedItem: KnowledgeItem | null
  detailOpen: boolean

  // 表单
  formOpen: boolean
  editingItem: KnowledgeItem | null
  formPrefill: Partial<KnowledgeItem> | null

  // 研究路线
  routes: ResearchRoute[]
  selectedRoute: ResearchRoute | null

  // AI 分析
  analysisResult: any | null
  analysisLoading: boolean
  selectedKnowledgeIds: string[]

  // 操作
  setItems: (items: KnowledgeItem[], total: number) => void
  setCategories: (categories: { name: string; count: number }[]) => void
  setSelectedCategory: (category: string | null) => void
  setSearchQuery: (query: string) => void
  setSelectedItem: (item: KnowledgeItem | null) => void
  setDetailOpen: (open: boolean) => void
  setFormOpen: (open: boolean) => void
  setEditingItem: (item: KnowledgeItem | null) => void
  setFormPrefill: (prefill: Partial<KnowledgeItem> | null) => void
  setRoutes: (routes: ResearchRoute[]) => void
  setSelectedRoute: (route: ResearchRoute | null) => void
  setAnalysisResult: (result: any | null) => void
  setAnalysisLoading: (loading: boolean) => void
  setSelectedKnowledgeIds: (ids: string[]) => void
  toggleKnowledgeSelection: (id: string) => void
  clearSelection: () => void
}

export const useKnowledgeStore = create<KnowledgeState>()(
  persist(
    (set, get) => ({
      items: [],
      total: 0,
      categories: [],
      selectedCategory: null,
      searchQuery: '',
      selectedItem: null,
      detailOpen: false,
      formOpen: false,
      editingItem: null,
      formPrefill: null,
      routes: [],
      selectedRoute: null,
      analysisResult: null,
      analysisLoading: false,
      selectedKnowledgeIds: [],

      setItems: (items, total) => set({ items, total }),
      setCategories: (categories) => set({ categories }),
      setSelectedCategory: (selectedCategory) => set({ selectedCategory }),
      setSearchQuery: (searchQuery) => set({ searchQuery }),
      setSelectedItem: (selectedItem) => set({ selectedItem, detailOpen: !!selectedItem }),
      setDetailOpen: (detailOpen) => set({ detailOpen, ...(detailOpen ? {} : { selectedItem: null }) }),
      setFormOpen: (formOpen) => set({ formOpen }),
      setEditingItem: (editingItem) => set({ editingItem }),
      setFormPrefill: (formPrefill) => set({ formPrefill }),
      setRoutes: (routes) => set({ routes }),
      setSelectedRoute: (selectedRoute) => set({ selectedRoute }),
      setAnalysisResult: (analysisResult) => set({ analysisResult }),
      setAnalysisLoading: (analysisLoading) => set({ analysisLoading }),
      setSelectedKnowledgeIds: (selectedKnowledgeIds) => set({ selectedKnowledgeIds }),
      toggleKnowledgeSelection: (id) => {
        const current = get().selectedKnowledgeIds
        if (current.includes(id)) {
          set({ selectedKnowledgeIds: current.filter((i) => i !== id) })
        } else {
          set({ selectedKnowledgeIds: [...current, id] })
        }
      },
      clearSelection: () => set({ selectedKnowledgeIds: [] }),
    }),
    {
      name: 'scholar-knowledge-state',
      partialize: (s) => ({
        selectedCategory: s.selectedCategory,
        analysisResult: s.analysisResult,
      }),
    }
  )
)
