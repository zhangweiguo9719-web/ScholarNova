import { BarChart3, Clock3, Layers3, Network } from 'lucide-react'
import type { ReactNode } from 'react'
import type { SearchRunDetail } from '@/api/types'
import { useLocaleStore } from '@/stores/localeStore'

interface SearchInsightsProps {
  run: SearchRunDetail
}

export default function SearchInsights({ run }: SearchInsightsProps) {
  const { locale } = useLocaleStore()
  const zh = locale === 'zh'
  const summary = run.result_summary
  const metrics = run.runtime_metrics

  if (!summary || !metrics || !summary.total) return null

  const latency = metrics.latency_ms
    ? metrics.latency_ms >= 1000
      ? `${(metrics.latency_ms / 1000).toFixed(1)}s`
      : `${Math.round(metrics.latency_ms)}ms`
    : '—'

  return (
    <section className="mt-4 rounded-2xl border border-gray-200/80 dark:border-gray-700/70 bg-white/85 dark:bg-gray-900/75 backdrop-blur-xl p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {zh ? '检索质量快照' : 'Retrieval quality snapshot'}
          </h2>
        </div>
        <span className="text-[11px] text-gray-500 dark:text-gray-400">
          {zh ? '无需额外模型调用' : 'No additional model call'}
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <Metric
          icon={<Layers3 className="w-3.5 h-3.5" />}
          label={zh ? '高度相关' : 'Highly relevant'}
          value={`${summary.highly_relevant ?? 0}`}
          tone="text-emerald-600 dark:text-emerald-400"
        />
        <Metric
          icon={<Network className="w-3.5 h-3.5" />}
          label={zh ? '部分相关' : 'Partially relevant'}
          value={`${summary.partially_relevant ?? 0}`}
          tone="text-amber-600 dark:text-amber-400"
        />
        <Metric
          icon={<BarChart3 className="w-3.5 h-3.5" />}
          label={zh ? 'API 调用' : 'API calls'}
          value={`${metrics.api_calls ?? 0} / ${metrics.search_rounds ?? 0}${zh ? '轮' : ' rounds'}`}
          tone="text-primary-600 dark:text-primary-400"
        />
        <Metric
          icon={<Clock3 className="w-3.5 h-3.5" />}
          label={zh ? '端到端耗时' : 'End-to-end'}
          value={latency}
          tone="text-sky-600 dark:text-sky-400"
        />
      </div>

      {!!summary.top_venues?.length && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-gray-500 dark:text-gray-400 mr-1">
            {zh ? '主要发表源' : 'Top venues'}
          </span>
          {summary.top_venues.slice(0, 4).map((venue) => (
            <span key={venue.name} className="badge bg-gray-100/90 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
              {venue.name} · {venue.count}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}

function Metric({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string
  tone: string
}) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-950/30 px-3 py-2.5">
      <div className={`flex items-center gap-1.5 text-[11px] ${tone}`}>
        {icon}
        <span>{label}</span>
      </div>
      <div className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  )
}
