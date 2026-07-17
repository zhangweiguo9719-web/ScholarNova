import axios from 'axios'
import type {
  SearchRequest,
  SearchResponse,
  SearchRunDetail,
  PaperDetail,
  AnalysisRequest,
  AnalysisResult,
  CompareRequest,
  CompareResult,
  RecommendationRequest,
  RecommendationResponse,
  RecommendationFeedback,
  ModelConfig,
  ModelTestRequest,
  ModelTestResponse,
  HealthResponse,
  EvidenceResponse,
  KnowledgeItem,
  KnowledgeListResponse,
  KnowledgeCreateRequest,
  KnowledgeUpdateRequest,
  ResearchRoute,
  RouteCreateRequest,
  AIAnalyzeResponse,
  RecommendResponse,
} from './types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 统一错误处理
    const message = error.response?.data?.detail || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

// =============================================================================
// 搜索 API
// =============================================================================

export const searchApi = {
  create: (request: SearchRequest) =>
    api.post<SearchResponse>('/search', request),

  getRun: (runId: string) =>
    api.get<SearchRunDetail>(`/search/${runId}`),
}

// =============================================================================
// 论文 API
// =============================================================================

export const papersApi = {
  get: (paperId: string) =>
    api.get<PaperDetail>(`/papers/${paperId}`),

  analyze: (paperId: string, request: AnalysisRequest) =>
    api.post<AnalysisResult>(`/papers/${paperId}/analyze`, request),

  compare: (request: CompareRequest) =>
    api.post<CompareResult>('/papers/compare', request),

  getEvidence: (runId: string, paperId: string) =>
    api.get<EvidenceResponse>(`/papers/${runId}/${paperId}/evidence`),

  translate: (text: string, targetLang: string = 'zh') =>
    api.post<{ translated: string; cached: boolean }>('/papers/translate', {
      text,
      target_lang: targetLang,
    }),

  journalQuality: (venue: string, quality?: unknown) =>
    api.post('/papers/journal-quality', { venue, quality }),

  rankingStatus: () => api.get('/papers/journal-rankings/status'),

  importRankings: (filename: string, content: string) =>
    api.post('/papers/journal-rankings/import', { filename, content }),
}

// =============================================================================
// 推荐 API
// =============================================================================

export const recommendationsApi = {
  get: (request: RecommendationRequest) =>
    api.post<RecommendationResponse>('/recommendations', request),

  submitFeedback: (feedback: RecommendationFeedback) =>
    api.post('/recommendations/feedback', feedback),
}

// =============================================================================
// 翻译 API
// =============================================================================

export const translateApi = {
  translate: (text: string, targetLang: string = 'zh') =>
    api.post<{ translated: string }>('/papers/translate', { text, target_lang: targetLang }),
}

// =============================================================================
// 模型配置 API
// =============================================================================

export const modelApi = {
  saveConfig: (config: ModelConfig) =>
    api.post('/model/config', config),

  testConnection: (request: ModelTestRequest) =>
    api.post<ModelTestResponse>('/model/test', request),
}

// =============================================================================
// 健康检查 API
// =============================================================================

export const healthApi = {
  check: () =>
    api.get<HealthResponse>('/health'),
}

export const networkApi = {
  getConfig: () => api.get('/network/config'),
  saveConfig: (data: {
    library_url?: string
    campus_proxy_url?: string
  }) => api.post('/network/config', data),
  detect: () => api.post('/network/detect'),
  libraryLink: (query: string) =>
    api.get('/network/library-link', { params: { q: query } }),
  testProxy: () => api.get('/network/proxy-test'),
}

// =============================================================================
// 知识库 API
// =============================================================================

export const knowledgeApi = {
  list: (category?: string) =>
    api.get<KnowledgeListResponse>('/knowledge', { params: category ? { category } : {} }),

  get: (id: string) =>
    api.get<KnowledgeItem>(`/knowledge/${id}`),

  create: (data: KnowledgeCreateRequest) =>
    api.post<KnowledgeItem>('/knowledge', data),

  update: (id: string, data: KnowledgeUpdateRequest) =>
    api.put<KnowledgeItem>(`/knowledge/${id}`, data),

  delete: (id: string) =>
    api.delete(`/knowledge/${id}`),

  getCategories: () =>
    api.get<{ name: string; count: number }[]>('/knowledge/categories'),

  aiAnalyze: (knowledgeIds: string[]) =>
    api.post<AIAnalyzeResponse>('/knowledge/ai-analyze', { knowledge_ids: knowledgeIds }),

  recommend: (knowledgeIds: string[], limit: number = 5) =>
    api.post<RecommendResponse>('/knowledge/recommend', { knowledge_ids: knowledgeIds, limit }),

  createRoute: (data: RouteCreateRequest) =>
    api.post<ResearchRoute>('/knowledge/routes', data),

  listRoutes: () =>
    api.get<{ items: ResearchRoute[]; total: number }>('/knowledge/routes'),

  getRoute: (id: string) =>
    api.get<ResearchRoute>(`/knowledge/routes/${id}`),

  updateRoute: (id: string, data: any) =>
    api.put<ResearchRoute>(`/knowledge/routes/${id}`, data),

  deleteRoute: (id: string) =>
    api.delete(`/knowledge/routes/${id}`),

  generateRouteAnalysis: (id: string) =>
    api.post<ResearchRoute>(`/knowledge/routes/${id}/ai-generate`),
}

export default api
