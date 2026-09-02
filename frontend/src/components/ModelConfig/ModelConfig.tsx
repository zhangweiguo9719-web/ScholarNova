import { useState } from 'react'
import { Save, TestTube, Loader2, Check, X, Globe, Cpu, ChevronDown, ChevronUp, Database, ShieldCheck } from 'lucide-react'
import clsx from 'clsx'
import { useLocaleStore } from '@/stores/localeStore'
import type { LLMProvider, ModelConfig as ModelConfigType, ModelTestResponse } from '@/api/types'
import './ModelConfig.css'

const providers: { value: LLMProvider; label: string; models: string[]; baseUrl?: string }[] = [
  { value: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'], baseUrl: 'https://api.openai.com/v1' },
  { value: 'anthropic', label: 'Anthropic', models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'], baseUrl: 'https://api.anthropic.com' },
  { value: 'ollama', label: 'Ollama (Local)', models: ['qwen2.5:14b', 'llama3:8b'], baseUrl: 'http://localhost:11434' },
  { value: 'mimo', label: 'Xiaomi MiMo', models: ['mimo-v2.5-pro', 'mimo-v2.5', 'mimo-v2-pro', 'mimo-v2-omni'], baseUrl: 'https://token-plan-cn.xiaomimimo.com/v1' },
  { value: 'deepseek', label: 'DeepSeek', models: ['deepseek-chat', 'deepseek-coder'], baseUrl: 'https://api.deepseek.com/v1' },
  { value: 'zhipu', label: 'ZhiPu (GLM)', models: ['glm-5.2', 'glm-5.1', 'glm-5-turbo', 'glm-4.7-flash', 'glm-4.5-flash'], baseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
  { value: 'qwen', label: 'Alibaba Qwen', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'], baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'moonshot', label: 'Moonshot (Kimi)', models: ['moonshot-v1-128k', 'moonshot-v1-32k'], baseUrl: 'https://api.moonshot.cn/v1' },
  { value: 'sensenova', label: 'SenseNova (商汤)', models: ['sensenova-u1-fast', 'sensenova-6.7-flash-lite', 'sensenova-6.5-pro'], baseUrl: 'https://token.sensenova.cn/v1' },
  { value: 'custom', label: 'Custom (OpenAI Compatible)', models: [] },
]

const embeddingProviders: { value: LLMProvider; label: string; models: string[]; baseUrl: string }[] = [
  { value: 'ollama', label: 'Ollama（本机，推荐）', models: ['nomic-embed-text', 'mxbai-embed-large', 'bge-m3'], baseUrl: 'http://localhost:11434' },
  { value: 'openai', label: 'OpenAI', models: ['text-embedding-3-small', 'text-embedding-3-large'], baseUrl: 'https://api.openai.com/v1' },
  { value: 'zhipu', label: '智谱 BigModel', models: ['embedding-3'], baseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
  { value: 'qwen', label: '阿里云百炼', models: ['text-embedding-v4'], baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'custom', label: 'OpenAI 兼容接口', models: [], baseUrl: '' },
]

// 任务类型定义
const taskTypes = [
  { key: 'analysis', icon: '📊', zhLabel: '论文分析', enLabel: 'Paper Analysis', desc: '论文深度分析、研究点提炼' },
  { key: 'query_planning', icon: '🔍', zhLabel: '查询规划', enLabel: 'Query Planning', desc: '自然语言查询解析和子查询生成' },
  { key: 'translation', icon: '🌐', zhLabel: '翻译', enLabel: 'Translation', desc: '摘要中英文翻译' },
  { key: 'vision', icon: '👁️', zhLabel: '图表/架构分析', enLabel: 'Vision', desc: '论文图表、架构图识别分析' },
  { key: 'recommendation', icon: '📄', zhLabel: '论文推荐', enLabel: 'Recommendation', desc: '基于知识库推荐新论文' },
  { key: 'assistant', icon: '🤖', zhLabel: '科研问答智能体', enLabel: 'Research Assistant', desc: '知识库与 Zotero 的可追溯问答' },
  { key: 'diagram', icon: '🎨', zhLabel: '图表生成', enLabel: 'Diagram Generation', desc: '研究架构图/流程图生成' },
]

interface ModelConfigProps {
  config: ModelConfigType
  testResult: ModelTestResponse | null
  isTesting: boolean
  isSaving: boolean
  onConfigChange: (partial: Partial<ModelConfigType>) => void
  onTest: () => void
  onSave: () => void
  fallbackTestResult: ModelTestResponse | null
  isFallbackTesting: boolean
  onFallbackTest: () => void
  embeddingTestResult: ModelTestResponse | null
  isEmbeddingTesting: boolean
  onEmbeddingTest: () => void
}

function TaskModelRow({ taskKey, icon, zhLabel, desc, currentConfig, defaultProvider, defaultModel, providerOptions, onChange }: {
  taskKey: string; icon: string; zhLabel: string; desc: string;
  currentConfig: { provider?: string; model_name?: string; api_key?: string; base_url?: string; api_key_configured?: boolean } | undefined;
  defaultProvider: string; defaultModel: string;
  providerOptions: typeof providers; onChange: (taskKey: string, cfg: any) => void;
}) {
  const { locale } = useLocaleStore()
  const isZh = locale === 'zh'
  const [expanded, setExpanded] = useState(false)

  const taskProvider = currentConfig?.provider || defaultProvider
  const taskModel = currentConfig?.model_name || defaultModel
  const taskApiKey = currentConfig?.api_key || ''
  const taskBaseUrl = currentConfig?.base_url || ''
  const p = providerOptions.find((pp) => pp.value === taskProvider)

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left">
        <span className="text-base">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-800 dark:text-gray-200">{zhLabel}</div>
          <div className="text-xs text-gray-400 dark:text-gray-500 truncate">{desc}</div>
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
          {taskModel || (isZh ? '使用默认模型' : 'Use default')}
        </span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {expanded && (
        <div className="p-3 space-y-2 border-t border-gray-200 dark:border-gray-700">
          {/* 提供商 + 模型 */}
          <div className="flex gap-2">
            <select value={taskProvider} onChange={(e) => {
              const nextProvider = providerOptions.find((option) => option.value === e.target.value)
              onChange(taskKey, {
                provider: e.target.value,
                model_name: nextProvider?.models[0] || '',
                api_key: '',
                api_key_configured: false,
                base_url: nextProvider?.baseUrl || '',
              })
            }}
              className="config-select flex-1">
              {providerOptions.map((pp) => <option key={pp.value} value={pp.value}>{pp.label}</option>)}
            </select>
            <input type="text" value={taskModel} onChange={(e) => onChange(taskKey, { model_name: e.target.value, provider: taskProvider, api_key: taskApiKey, base_url: taskBaseUrl })}
              placeholder={p?.models[0] || 'model name'} className="config-input flex-1" />
          </div>
          {/* API Key */}
          <div>
            <label className="text-xs text-gray-400 dark:text-gray-500 block mb-0.5">{isZh ? 'API Key（可选，留空用默认）' : 'API Key (optional, uses default if empty)'}</label>
            <input type="password" value={taskApiKey} onChange={(e) => onChange(taskKey, { api_key: e.target.value, provider: taskProvider, model_name: taskModel, base_url: taskBaseUrl })}
              placeholder={currentConfig?.api_key_configured ? (isZh ? '已安全保存在本机后端' : 'Saved securely by the local backend') : (isZh ? '留空使用默认' : 'Leave empty for default')} className="config-input text-xs" />
          </div>
          {/* Base URL */}
          <div>
            <label className="text-xs text-gray-400 dark:text-gray-500 block mb-0.5">{isZh ? 'API 地址（可选，留空用默认）' : 'Base URL (optional, uses default if empty)'}</label>
            <input type="text" value={taskBaseUrl} onChange={(e) => onChange(taskKey, { base_url: e.target.value, provider: taskProvider, model_name: taskModel, api_key: taskApiKey })}
              placeholder={isZh ? '留空使用默认' : 'Leave empty for default'} className="config-input text-xs" />
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {isZh ? '所有字段留空则使用上方的默认模型配置' : 'Leave all fields empty to use the default model config'}
          </p>
        </div>
      )}
    </div>
  )
}

export default function ModelConfig({ config, testResult, isTesting, isSaving, onConfigChange, onTest, onSave, fallbackTestResult, isFallbackTesting, onFallbackTest, embeddingTestResult, isEmbeddingTesting, onEmbeddingTest }: ModelConfigProps) {
  const { t, locale } = useLocaleStore()
  const isZh = locale === 'zh'
  const selectedProvider = providers.find((p) => p.value === config.provider)
  const [showTaskModels, setShowTaskModels] = useState(false)
  const fallback = config.fallback || {
    enabled: false,
    provider: 'qwen' as LLMProvider,
    model_name: 'qwen-plus',
    api_key: '',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  }
  const selectedFallbackProvider = providers.find((p) => p.value === fallback.provider)
  const embedding = config.embedding || {
    enabled: false,
    provider: 'ollama' as LLMProvider,
    model_name: 'nomic-embed-text',
    api_key: '',
    base_url: 'http://localhost:11434',
  }
  const selectedEmbeddingProvider = embeddingProviders.find((p) => p.value === embedding.provider)

  const handleTaskChange = (taskKey: string, cfg: any) => {
    const tasks = { ...(config.tasks || {}), [taskKey]: cfg }
    onConfigChange({ tasks } as any)
  }

  return (
    <div className="model-config card animate-fade-in">
      <div className="model-config-header">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">LLM {t('settings.modelConfig')}</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('settings.modelConfig')}</p>
      </div>

      <div className="model-config-body">
        {/* Provider */}
        <div className="config-field">
          <label className="config-label">{t('settings.provider')}</label>
          <select value={config.provider}
            onChange={(e) => {
              const newProvider = e.target.value as LLMProvider
              const p = providers.find((pp) => pp.value === newProvider)
              const newModel = p?.models[0] || ''
              onConfigChange({
                provider: newProvider,
                model_name: newModel,
                api_key: '',
                api_key_configured: false,
                base_url: p?.baseUrl || '',
              })
            }}
            className="config-select">
            {providers.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </div>

        {/* Model */}
        <div className="config-field">
          <label className="config-label">{t('settings.modelName')}</label>
          <div className="flex gap-2">
            {selectedProvider && selectedProvider.models.length > 0 && (
              <select value={config.model_name} onChange={(e) => onConfigChange({ model_name: e.target.value })} className="config-select flex-1">
                {selectedProvider.models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            )}
            <input type="text" value={config.model_name} onChange={(e) => onConfigChange({ model_name: e.target.value })}
              placeholder={t('settings.modelNamePlaceholder')} className="config-input flex-1" />
          </div>
        </div>

        {/* API Key */}
        {config.provider !== 'ollama' && (
          <div className="config-field">
            <label className="config-label">{t('settings.apiKey')}</label>
            <input type="password" value={config.api_key || ''} onChange={(e) => onConfigChange({ api_key: e.target.value })}
              placeholder={config.api_key_configured ? t('settings.apiKeySaved') : t('settings.apiKeyPlaceholder')} className="config-input" />
          </div>
        )}

        {/* Base URL */}
        <div className="config-field">
          <label className="config-label"><Globe className="w-4 h-4 inline mr-1" />{t('settings.apiBase')}</label>
          <input type="text" value={config.base_url || ''} onChange={(e) => onConfigChange({ base_url: e.target.value })}
            placeholder={selectedProvider?.baseUrl || 'https://api.openai.com/v1'} className="config-input" />
          {config.provider === 'mimo' && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              OpenAI 兼容：https://token-plan-cn.xiaomimimo.com/v1<br/>
              Anthropic 兼容：https://token-plan-cn.xiaomimimo.com/anthropic
            </p>
          )}
        </div>

        {/* Temperature & Max Tokens */}
        <div className="grid grid-cols-2 gap-3">
          <div className="config-field">
            <label className="config-label">Temperature: <span className="font-mono">{config.temperature?.toFixed(1) ?? '0.7'}</span></label>
            <input type="range" min="0" max="2" step="0.1" value={config.temperature ?? 0.7}
              onChange={(e) => onConfigChange({ temperature: parseFloat(e.target.value) })} className="config-range" />
          </div>
          <div className="config-field">
            <label className="config-label">Max Tokens</label>
            <input type="number" value={config.max_tokens ?? 4096}
              onChange={(e) => onConfigChange({ max_tokens: parseInt(e.target.value) || 4096 })}
              min="1" max="128000" className="config-input" />
          </div>
        </div>

        {/* 多模型配置开关 */}
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <button onClick={() => setShowTaskModels(!showTaskModels)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors text-sm font-medium">
            <Cpu className="w-4 h-4" />
            {showTaskModels ? '收起任务模型配置' : '按任务类型配置不同模型'}
            {showTaskModels ? <ChevronUp className="w-4 h-4 ml-auto" /> : <ChevronDown className="w-4 h-4 ml-auto" />}
          </button>
        </div>

        {showTaskModels && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              为不同任务指定不同模型。留空则使用上方的默认模型。
            </p>
            {taskTypes.map((task) => (
              <TaskModelRow key={task.key} taskKey={task.key} icon={task.icon} zhLabel={task.zhLabel}
                desc={task.desc} currentConfig={config.tasks?.[task.key]}
                defaultProvider={config.provider || 'mimo'} defaultModel={config.model_name || 'mimo-v2.5-pro'}
                providerOptions={providers} onChange={handleTaskChange} />
            ))}
          </div>
        )}

        <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex gap-3">
              <div className="mt-0.5 rounded-lg bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400"><Cpu className="h-4 w-4" /></div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {isZh ? '备用文本模型（可选）' : 'Fallback text model (optional)'}
                </h3>
                <p className="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
                  {isZh
                    ? '当前用于科研问答：仅当主模型最终失败时尝试一次，不参与视觉与出图。每次尝试都会独立记录 Token。'
                    : 'Currently used by the research assistant: tried once only after the primary model fails, never for vision or image generation. Tokens are tracked per attempt.'}
                </p>
              </div>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input type="checkbox" className="peer sr-only" checked={fallback.enabled}
                onChange={(event) => onConfigChange({ fallback: { ...fallback, enabled: event.target.checked } })} />
              <span className="h-6 w-11 rounded-full bg-gray-300 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:bg-amber-500 peer-checked:after:translate-x-5 dark:bg-gray-700" />
            </label>
          </div>

          {fallback.enabled && (
            <div className="mt-4 space-y-3 border-t border-amber-500/15 pt-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="config-label">{isZh ? '备用提供商' : 'Fallback provider'}</label>
                  <select className="config-select" value={fallback.provider} onChange={(event) => {
                    const next = providers.find((provider) => provider.value === event.target.value) || providers[0]
                    onConfigChange({ fallback: { enabled: true, provider: next.value, model_name: next.models[0] || '', api_key: '', api_key_configured: false, base_url: next.baseUrl || '' } })
                  }}>
                    {providers.map((provider) => <option key={provider.value} value={provider.value}>{provider.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="config-label">{isZh ? '备用模型' : 'Fallback model'}</label>
                  <input className="config-input" value={fallback.model_name || ''}
                    onChange={(event) => onConfigChange({ fallback: { ...fallback, model_name: event.target.value } })}
                    placeholder={selectedFallbackProvider?.models[0] || 'model name'} />
                </div>
              </div>
              {fallback.provider !== 'ollama' && (
                <div>
                  <label className="config-label">API Key</label>
                  <input type="password" className="config-input" value={fallback.api_key || ''}
                    onChange={(event) => onConfigChange({ fallback: { ...fallback, api_key: event.target.value } })}
                    placeholder={fallback.api_key_configured ? (isZh ? '已安全保存在本机后端' : 'Saved by the local backend') : (isZh ? '备用模型独立 API Key' : 'Independent fallback API key')} />
                </div>
              )}
              <div>
                <label className="config-label"><Globe className="mr-1 inline h-4 w-4" />API Base URL</label>
                <input className="config-input" value={fallback.base_url || ''}
                  onChange={(event) => onConfigChange({ fallback: { ...fallback, base_url: event.target.value } })}
                  placeholder={selectedFallbackProvider?.baseUrl || 'https://…/v1'} />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-500/15 bg-white/50 px-3 py-2 dark:bg-gray-900/20">
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  {isZh ? '不会因开启而常态双调用；只有主模型失败后才会产生备用调用。' : 'Enabling this does not duplicate normal calls; fallback is invoked only after primary failure.'}
                </p>
                <button type="button" onClick={onFallbackTest} disabled={isFallbackTesting || !fallback.model_name}
                  className="config-btn config-btn-secondary !px-3 !py-1.5">
                  {isFallbackTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube className="h-4 w-4" />}
                  {isZh ? '测试备用模型' : 'Test fallback'}
                </button>
              </div>
              {fallbackTestResult && (
                <div className={clsx('config-test-result', fallbackTestResult.success ? 'config-test-success' : 'config-test-fail')}>
                  <div className="flex items-center gap-2">
                    {fallbackTestResult.success ? <Check className="h-4 w-4 text-green-600" /> : <X className="h-4 w-4 text-red-600" />}
                    <span className="text-sm font-medium">{fallbackTestResult.success ? (isZh ? '备用模型连接成功' : 'Fallback connected') : fallbackTestResult.error}</span>
                  </div>
                  {fallbackTestResult.latency_ms != null && <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">Latency: {fallbackTestResult.latency_ms.toFixed(0)}ms</p>}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50/70 p-4 dark:border-gray-700 dark:bg-gray-800/30">
          <div className="flex items-start justify-between gap-4">
            <div className="flex gap-3">
              <div className="mt-0.5 rounded-lg bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400"><Database className="h-4 w-4" /></div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {isZh ? '语义检索增强（可选）' : 'Semantic retrieval (optional)'}
                </h3>
                <p className="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
                  {isZh ? '使用独立 Embedding 模型与 BM25 做 RRF 融合。未配置或调用失败时自动退回 BM25。' : 'Fuse an independent embedding model with BM25 using RRF. Failures automatically fall back to BM25.'}
                </p>
              </div>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input type="checkbox" className="peer sr-only" checked={embedding.enabled}
                onChange={(event) => onConfigChange({ embedding: { ...embedding, enabled: event.target.checked } })} />
              <span className="h-6 w-11 rounded-full bg-gray-300 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:bg-amber-500 peer-checked:after:translate-x-5 dark:bg-gray-700" />
            </label>
          </div>

          {embedding.enabled && (
            <div className="mt-4 space-y-3 border-t border-gray-200 pt-4 dark:border-gray-700">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="config-label">{isZh ? 'Embedding 提供商' : 'Embedding provider'}</label>
                  <select value={embedding.provider} className="config-select" onChange={(event) => {
                    const next = embeddingProviders.find((provider) => provider.value === event.target.value) || embeddingProviders[0]
                    onConfigChange({ embedding: { enabled: true, provider: next.value, model_name: next.models[0] || '', api_key: '', api_key_configured: false, base_url: next.baseUrl } })
                  }}>
                    {embeddingProviders.map((provider) => <option key={provider.value} value={provider.value}>{provider.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="config-label">{isZh ? 'Embedding 模型' : 'Embedding model'}</label>
                  <input className="config-input" value={embedding.model_name}
                    onChange={(event) => onConfigChange({ embedding: { ...embedding, model_name: event.target.value } })}
                    placeholder={selectedEmbeddingProvider?.models[0] || 'embedding model'} />
                </div>
              </div>
              {embedding.provider !== 'ollama' && (
                <div>
                  <label className="config-label">API Key</label>
                  <input type="password" className="config-input" value={embedding.api_key || ''}
                    onChange={(event) => onConfigChange({ embedding: { ...embedding, api_key: event.target.value } })}
                    placeholder={embedding.api_key_configured ? (isZh ? '已安全保存在本机后端' : 'Saved by the local backend') : 'Embedding API Key'} />
                </div>
              )}
              <div>
                <label className="config-label"><Globe className="mr-1 inline h-4 w-4" />API Base URL</label>
                <input className="config-input" value={embedding.base_url || ''}
                  onChange={(event) => onConfigChange({ embedding: { ...embedding, base_url: event.target.value } })}
                  placeholder={selectedEmbeddingProvider?.baseUrl || 'https://…/v1'} />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-500/15 bg-emerald-500/5 px-3 py-2">
                <p className="inline-flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-400"><ShieldCheck className="h-3.5 w-3.5" />{isZh ? '向量缓存在本地数据库；聊天 Key 与 Embedding Key 相互独立。' : 'Vectors are cached locally; chat and embedding credentials stay independent.'}</p>
                <button type="button" onClick={onEmbeddingTest} disabled={isEmbeddingTesting || !embedding.model_name}
                  className="config-btn config-btn-secondary !px-3 !py-1.5">
                  {isEmbeddingTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube className="h-4 w-4" />}
                  {isZh ? '测试语义模型' : 'Test embedding'}
                </button>
              </div>
              {embeddingTestResult && (
                <div className={clsx('config-test-result', embeddingTestResult.success ? 'config-test-success' : 'config-test-fail')}>
                  <div className="flex items-center gap-2">
                    {embeddingTestResult.success ? <Check className="h-4 w-4 text-green-600" /> : <X className="h-4 w-4 text-red-600" />}
                    <span className="text-sm font-medium">{embeddingTestResult.success ? (isZh ? `连接成功 · ${embeddingTestResult.model_info?.dimensions || 0} 维` : `Connected · ${embeddingTestResult.model_info?.dimensions || 0} dimensions`) : embeddingTestResult.error}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={clsx('config-test-result', testResult.success ? 'config-test-success' : 'config-test-fail')}>
            <div className="flex items-center gap-2 mb-1">
              {testResult.success ? <Check className="w-4 h-4 text-green-600" /> : <X className="w-4 h-4 text-red-600" />}
              <span className="text-sm font-medium">{testResult.success ? t('settings.connectionSuccess') : t('settings.connectionFailed')}</span>
            </div>
            {testResult.latency_ms != null && <p className="text-xs text-gray-600 dark:text-gray-400">Latency: {testResult.latency_ms.toFixed(0)}ms</p>}
            {testResult.error && <p className="text-xs text-red-600 dark:text-red-400 mt-1">{testResult.error}</p>}
          </div>
        )}

        {/* Actions */}
        <div className="config-actions">
          <button onClick={onTest} disabled={isTesting} className="config-btn config-btn-secondary">
            {isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
            {t('settings.testConnection')}
          </button>
          <button onClick={onSave} disabled={isSaving} className="config-btn config-btn-primary">
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {t('settings.saveConfig')}
          </button>
        </div>
      </div>
    </div>
  )
}
