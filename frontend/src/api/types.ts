// =============================================================================
// 枚举类型
// =============================================================================

export type DataSource = 'semantic_scholar' | 'openalex' | 'crossref' | 'arxiv'

export type SearchStatus = 'pending' | 'running' | 'completed' | 'failed'

export type Verdict = 'supports' | 'contradicts' | 'neutral' | 'insufficient'

export type FeedbackType = 'helpful' | 'not_helpful' | 'saved' | 'dismissed'

export type AnalysisType = 'summary' | 'methodology' | 'findings' | 'pros_cons' | 'full'

export type LLMProvider = 'openai' | 'anthropic' | 'ollama' | 'mimo' | 'deepseek' | 'zhipu' | 'qwen' | 'moonshot' | 'sensenova' | 'custom'

// =============================================================================
// 请求类型
// =============================================================================

export interface SearchRequest {
  query: string
  max_results?: number
  sources?: DataSource[]
  date_from?: string
  date_to?: string
  min_citations?: number
  open_access_only?: boolean
}

export interface AnalysisRequest {
  query: string
  analysis_type?: AnalysisType
}

export interface CompareRequest {
  paper_ids: string[]
  query: string
}

export interface RecommendationRequest {
  user_id?: string
  context?: string
  limit?: number
}

export interface RecommendationFeedback {
  recommendation_id: string
  feedback_type: FeedbackType
  comment?: string
}

export interface TaskModelConfig {
  provider?: LLMProvider
  model_name?: string
  api_key?: string
  base_url?: string
}

export interface ModelConfig {
  provider: LLMProvider
  model_name: string
  api_key?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
  tasks?: Record<string, TaskModelConfig>
}

export interface ModelTestRequest {
  provider: LLMProvider
  model_name: string
  api_key?: string
  base_url?: string
}

// =============================================================================
// 响应类型
// =============================================================================

export interface SubQuery {
  query: string
  source: DataSource
  rationale: string
}

export interface QueryPlan {
  sub_queries: SubQuery[]
  strategy: string
  intent?: string | null
  keywords?: string[]
  constraints?: Array<{
    key: string
    operator: string
    value: unknown
    description?: string | null
  }>
  entities?: Record<string, string[]>
  expanded_queries?: string[]
}

export interface SearchResponse {
  run_id: string
  status: SearchStatus
  query_plan: QueryPlan | null
  message: string
}

export interface SearchProgress {
  total_sources: number
  completed_sources: number
  total_papers: number
  deduplicated_papers: number
  current_phase: string
  search_rounds?: number
  api_calls?: number
  latency_ms?: number
}

export interface Paper {
  id: string
  title: string
  authors: string[]
  abstract: string | null
  year: number | null
  venue: string | null
  citation_count: number
  doi: string | null
  url: string | null
  pdf_url: string | null
  source: DataSource
  corpus_id?: string | null
  relevance_score: number | null
  is_open_access: boolean
  quality?: {
    quality_score: number
    citation_percentile: number
    citation_velocity: number
    impact_label: 'highly_cited' | 'well_cited' | 'established' | 'emerging' | 'limited_signal'
    citation_basis: 'result_set' | string
    wos_indexed: boolean | null
    jcr_quartile: string | null
    cas_quartile: string | null
    partition_year: number | null
    partition_status: 'verified' | 'unverified' | string
    partition_source: string | null
  } | null
}

export interface PaperReference {
  id: string
  title: string
  year: number | null
  citation_count: number
}

export interface PaperDetail extends Paper {
  references: PaperReference[]
  citations: PaperReference[]
  fields_of_study: string[]
  keywords: string[]
  publication_date: string | null
  volume: string | null
  issue: string | null
  pages: string | null
}

export interface SearchRunDetail {
  run_id: string
  status: SearchStatus
  original_query: string
  query_plan: QueryPlan | null
  progress: SearchProgress | null
  results: Paper[]
  source_status?: Array<{
    source: string
    success: boolean
    paper_count: number
    elapsed_ms: number
    error?: string | null
  }>
  runtime_metrics?: {
    api_calls?: number
    search_rounds?: number
    latency_ms?: number
    successful_calls?: number
    failed_calls?: number
    token_usage?: Record<string, unknown>
  }
  result_summary?: {
    total?: number
    highly_relevant?: number
    partially_relevant?: number
    other?: number
    year_range?: number[]
    top_venues?: Array<{ name: string; count: number }>
    intent?: string | null
    entity_dimensions?: Record<string, string[]>
  }
  created_at: string
  completed_at: string | null
}

export interface AnalysisResult {
  paper_id: string
  analysis_type: AnalysisType
  summary: string
  methodology: string | null
  key_findings: string[]
  strengths: string[]
  weaknesses: string[]
  relevance_to_query: string | null
  created_at: string
}

export interface CompareResult {
  papers: Array<{
    paper_id: string
    title: string
  }>
  comparison: {
    methodology: string
    results: string
    strengths_weaknesses: string
    recommendation: string
  }
  created_at: string
}

export interface EvidenceSpan {
  id: string
  run_id: string
  paper_id: string
  claim: string
  evidence_text: string
  verdict: Verdict
  confidence: number
  page_number: number | null
  section: string | null
  context: string | null
  llm_model: string | null
  created_at: string
}

export interface EvidenceResponse {
  paper_id: string
  run_id: string
  evidence_spans: EvidenceSpan[]
}

export interface Recommendation {
  id: string
  paper: Paper
  score: number
  reason: string
}

export interface RecommendationResponse {
  recommendations: Recommendation[]
  has_more: boolean
}

export interface ModelTestResponse {
  success: boolean
  latency_ms: number | null
  model_info: {
    provider: string
    model: string
    context_window?: number
  } | null
  error: string | null
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  timestamp: string
  services: {
    database: 'connected' | 'disconnected'
    redis: 'connected' | 'disconnected'
    llm: 'available' | 'unavailable'
  }
}

export interface SuccessResponse {
  success: boolean
  message: string
}

export interface TranslateResponse {
  translated: string
}

// =============================================================================
// 知识库类型
// =============================================================================

export interface KnowledgeItem {
  id: string
  title: string
  category: string
  content: string
  source_paper_id: string | null
  source_paper_title: string | null
  source_paper_doi: string | null
  research_points: string[]
  tags: string[]
  notes: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeListResponse {
  items: KnowledgeItem[]
  total: number
  categories: { name: string; count: number }[]
}

export interface KnowledgeCreateRequest {
  title: string
  category: string
  content: string
  source_paper_id?: string | null
  source_paper_title?: string | null
  source_paper_doi?: string | null
  research_points?: string[]
  tags?: string[]
  notes?: string | null
  auto_polish?: boolean
  card_type?: string
  card_data?: Record<string, any>
}

export interface KnowledgeUpdateRequest extends Partial<KnowledgeCreateRequest> {}

export interface ResearchRoute {
  id: string
  title: string
  description: string
  knowledge_ids: string[]
  ai_analysis: string
  status: string
  created_at: string
}

export interface RouteCreateRequest {
  title: string
  description?: string
  knowledge_ids?: string[]
}

export interface AIAnalyzeRequest {
  knowledge_ids: string[]
}

export interface AIAnalyzeResponse {
  analysis: string
  research_directions: string[]
  architecture_description: string
  suggested_routes: string[]
  recommended_papers: string[]
}

export interface RecommendRequest {
  knowledge_ids: string[]
  limit: number
}

export interface RecommendResponse {
  recommendations: {
    title: string
    reason: string
    relevance_score: number
  }[]
}
