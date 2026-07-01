import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ModelConfig, ModelTestResponse } from '@/api/types'

interface ModelState {
  config: ModelConfig
  testResult: ModelTestResponse | null
  isTesting: boolean
  isSaving: boolean

  setConfig: (config: Partial<ModelConfig>) => void
  setFullConfig: (config: ModelConfig) => void
  setTestResult: (result: ModelTestResponse | null) => void
  setIsTesting: (testing: boolean) => void
  setIsSaving: (saving: boolean) => void
  reset: () => void
}

const defaultConfig: ModelConfig = {
  provider: 'mimo',
  model_name: 'mimo-v2.5-pro',
  api_key: '',
  base_url: 'https://token-plan-cn.xiaomimimo.com/v1',
  temperature: 0.7,
  max_tokens: 4096,
  tasks: {
    analysis: { provider: 'mimo', model_name: 'mimo-v2.5-pro' },       // 文字分析
    query_planning: { provider: 'mimo', model_name: 'mimo-v2.5-pro' }, // 查询规划
    translation: { provider: 'mimo', model_name: 'mimo-v2.5-pro' },    // 翻译
    vision: { provider: 'mimo', model_name: 'mimo-v2.5' },             // 视觉/多模态
    recommendation: { provider: 'mimo', model_name: 'mimo-v2.5-pro' }, // 推荐
    diagram: { provider: 'sensenova', model_name: 'sensenova-u1-fast', api_key: '', base_url: 'https://token.sensenova.cn/v1' }, // 仅出图
  },
}

export const useModelStore = create<ModelState>()(
  persist(
    (set) => ({
      config: { ...defaultConfig },
      testResult: null,
      isTesting: false,
      isSaving: false,

      setConfig: (partial) =>
        set((state) => ({
          config: { ...state.config, ...partial },
        })),

      setFullConfig: (config) => set({ config }),

      setTestResult: (testResult) => set({ testResult }),
      setIsTesting: (isTesting) => set({ isTesting }),
      setIsSaving: (isSaving) => set({ isSaving }),

      reset: () =>
        set({
          config: { ...defaultConfig },
          testResult: null,
          isTesting: false,
          isSaving: false,
        }),
    }),
    {
      name: 'scholar-agent-model-config',
      partialize: (state) => ({ config: state.config }),
    }
  )
)
