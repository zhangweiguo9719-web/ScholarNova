import { useState, useEffect } from 'react'
import { Globe, Loader2, RefreshCw, ExternalLink, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import api from '@/api/client'

export default function NetworkConfig() {
  const [libraryUrl, setLibraryUrl] = useState('https://lib.lut.edu.cn/index')
  const [status, setStatus] = useState<Record<string, boolean | null>>({})
  const [detecting, setDetecting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    api.get('/network/config').then((r: any) => {
      setLibraryUrl(r.data.proxy_url || 'https://lib.lut.edu.cn/index')
      setStatus(r.data.results || {})
    }).catch(() => {})
  }, [])

  const handleDetect = async () => {
    setDetecting(true)
    try {
      const r: any = await api.post('/network/detect')
      setStatus(r.data.results)
      toast.success('网络检测完成')
    } catch { toast.error('检测失败') }
    finally { setDetecting(false) }
  }

  const handleSave = async () => {
    try {
      await api.post('/network/config', { proxy_url: libraryUrl })
      setSaved(true)
      toast.success('配置已保存')
      setTimeout(() => setSaved(false), 2000)
    } catch { toast.error('保存失败') }
  }

  const campusOk = status.campus_proxy === true
  const gsOk = status.google_scholar === true

  return (
    <div className="space-y-4">
      {/* 网络状态 */}
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary-500" />
            可用数据源
          </h4>
          <button onClick={handleDetect} disabled={detecting}
            className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1">
            {detecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            重新检测
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { key: 'crossref', label: 'CrossRef', free: true, ok: status.crossref },
            { key: 'semantic_scholar', label: 'Semantic Scholar', free: true, ok: status.semantic_scholar },
            { key: 'openalex', label: 'OpenAlex', free: true, ok: status.openalex },
            { key: 'google_scholar', label: 'Google Scholar', free: false, ok: gsOk },
            { key: 'campus_proxy', label: '学校图书馆', free: false, ok: campusOk },
          ].map(({ key, label, free, ok }) => (
            <div key={key} className="flex items-center gap-2 text-xs p-2 rounded bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700">
              <span className={clsx('w-2.5 h-2.5 rounded-full', ok === true ? 'bg-green-500' : ok === false ? 'bg-red-500' : 'bg-gray-300')} />
              <span className="text-gray-600 dark:text-gray-400">{label}</span>
              {free && <span className="text-[10px] text-green-600 dark:text-green-400 ml-auto">免费</span>}
            </div>
          ))}
        </div>
      </div>

      {/* 重要提醒 */}
      <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-800/30">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-700 dark:text-amber-300">
            <p className="font-medium mb-1">⚠️ 校园网与 VPN 不能同时使用</p>
            <p className="text-amber-600 dark:text-amber-400">
              校园网环境下无法使用 VPN 翻墙访问 Google Scholar 等境外资源。
              反之，使用 VPN 时无法访问学校图书馆订阅的数据库。请根据需求选择网络环境。
            </p>
          </div>
        </div>
      </div>

      {/* 学校图书馆 */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800/30">
        <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-2 flex items-center gap-2">
          🏫 连接学校图书馆
        </h4>
        <p className="text-xs text-blue-600 dark:text-gray-400 mb-2">
          在校园网环境下，填写图书馆网址即可访问 IEEE、ACM、Elsevier 等订阅数据库。
          <span className="text-amber-600 dark:text-amber-400 ml-1">搜索时会自动通过校园网检索。</span>
        </p>

        <button onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 mb-3">
          {showAdvanced ? '收起' : '高级配置'}
          {showAdvanced ? '▲' : '▼'}
        </button>

        {showAdvanced && (
          <div className="space-y-2">
            <input type="text" value={libraryUrl}
              onChange={(e) => setLibraryUrl(e.target.value)}
              placeholder="https://lib.lut.edu.cn/index"
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 outline-none" />
            <div className="flex gap-2">
              <a href={libraryUrl} target="_blank" rel="noopener noreferrer"
                className="px-3 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-1">
                <ExternalLink className="w-3 h-3" /> 访问图书馆
              </a>
              <button onClick={handleSave}
                className="px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                {saved ? '✅ 已保存' : '保存配置'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
