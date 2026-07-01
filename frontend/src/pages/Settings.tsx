import toast from 'react-hot-toast'
import { modelApi } from '@/api/client'
import { useModelStore } from '@/stores/modelStore'
import { useLocaleStore } from '@/stores/localeStore'
import ModelConfig from '@/components/ModelConfig/ModelConfig'
import NetworkConfig from '@/components/NetworkConfig'

export default function Settings() {
  const { t } = useLocaleStore()
  const {
    config,
    testResult,
    isTesting,
    isSaving,
    setConfig,
    setTestResult,
    setIsTesting,
    setIsSaving,
  } = useModelStore()

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)

    try {
      const response = await modelApi.testConnection({
        provider: config.provider,
        model_name: config.model_name,
        api_key: config.api_key,
        base_url: config.base_url,
      })
      setTestResult(response.data)
    } catch (err: any) {
      setTestResult({
        success: false,
        latency_ms: null,
        model_info: null,
        error: err.response?.data?.detail || t('settings.connectionFailed'),
      })
    } finally {
      setIsTesting(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)

    try {
      await modelApi.saveConfig(config)
      toast.success(t('settings.connectionSuccess'))
    } catch (err: any) {
      toast.error(err.response?.data?.detail || t('settings.connectionFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] bg-gray-50 dark:bg-gray-950 px-4 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{t('settings.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {t('settings.modelConfig')}
          </p>
        </div>

        <ModelConfig
          config={config}
          testResult={testResult}
          isTesting={isTesting}
          isSaving={isSaving}
          onConfigChange={setConfig}
          onTest={handleTest}
          onSave={handleSave}
        />

        <div className="mt-6">
          <NetworkConfig />
        </div>
      </div>
    </div>
  )
}
