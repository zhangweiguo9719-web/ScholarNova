import { useState } from 'react'
import { Save, TestTube, Loader2, Check, X, Globe, Cpu, ChevronDown, ChevronUp } from 'lucide-react'
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
  { value: 'zhipu', label: 'ZhiPu (GLM)', models: ['glm-4-plus', 'glm-4-flash'], baseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
  { value: 'qwen', label: 'Alibaba Qwen', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'], baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'moonshot', label: 'Moonshot (Kimi)', models: ['moonshot-v1-128k', 'moonshot-v1-32k'], baseUrl: 'https://api.moonshot.cn/v1' },
  { value: 'sensenova', label: 'SenseNova (商汤)', models: ['sensenova-u1-fast', 'sensenova-6.7-flash-lite', 'sensenova-6.5-pro'], baseUrl: 'https://token.sensenova.cn/v1' },
  { value: 'custom', label: 'Custom (OpenAI Compatible)', models: [] },
]

// 任务类型定义
const taskTypes = [
  { key: 'analysis', icon: '📊', zhLabel: '论文分析', enLabel: 'Paper Analysis', desc: '论文深度分析、研究点提炼' },
  { key: 'query_planning', icon: '🔍', zhLabel: '查询规划', enLabel: 'Query Planning', desc: '自然语言查询解析和子查询生成' },
  { key: 'translation', icon: '🌐', zhLabel: '翻译', enLabel: 'Translation', desc: '摘要中英文翻译' },
  { key: 'vision', icon: '👁️', zhLabel: '图表/架构分析', enLabel: 'Vision', desc: '论文图表、架构图识别分析' },
  { key: 'recommendation', icon: '📄', zhLabel: '论文推荐', enLabel: 'Recommendation', desc: '基于知识库推荐新论文' },
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
}

function TaskModelRow({ taskKey, icon, zhLabel, desc, currentConfig, defaultProvider, defaultModel, providerOptions, onChange }: {
  taskKey: string; icon: string; zhLabel: string; desc: string;
  currentConfig: { provider?: string; model_name?: string; api_key?: string; base_url?: string } | undefined;
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
            <select value={taskProvider} onChange={(e) => onChange(taskKey, { provider: e.target.value, model_name: '', api_key: taskApiKey, base_url: taskBaseUrl })}
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
              placeholder={isZh ? '留空使用默认' : 'Leave empty for default'} className="config-input text-xs" />
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

export default function ModelConfig({ config, testResult, isTesting, isSaving, onConfigChange, onTest, onSave }: ModelConfigProps) {
  const { t } = useLocaleStore()
  const selectedProvider = providers.find((p) => p.value === config.provider)
  const [showTaskModels, setShowTaskModels] = useState(false)

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
              // 更新主配置 + 所有任务模型的提供商
              const newTasks: Record<string, any> = {}
              for (const [key, val] of Object.entries(config.tasks || {})) {
                newTasks[key] = { ...val, provider: newProvider }
              }
              onConfigChange({ provider: newProvider, model_name: newModel, base_url: p?.baseUrl || '', tasks: newTasks })
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
              placeholder={t('settings.apiKeyPlaceholder')} className="config-input" />
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
