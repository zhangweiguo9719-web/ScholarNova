import { ShieldCheck, Loader2, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import type { EvidenceSpan, Verdict } from '@/api/types'
import './EvidencePanel.css'

const verdictConfig: Record<Verdict, { label: string; color: string; icon: string }> = {
  supports: { label: 'Supports', color: 'badge-verdict-supports', icon: '+' },
  contradicts: { label: 'Contradicts', color: 'badge-verdict-contradicts', icon: '-' },
  neutral: { label: 'Neutral', color: 'badge-verdict-neutral', icon: '~' },
  insufficient: { label: 'Insufficient', color: 'badge-verdict-insufficient', icon: '?' },
}

interface EvidencePanelProps {
  spans: EvidenceSpan[]
  loading: boolean
}

export default function EvidencePanel({ spans, loading }: EvidencePanelProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
        <span className="ml-2 text-sm text-gray-500">Loading evidence...</span>
      </div>
    )
  }

  if (spans.length === 0) {
    return (
      <div className="evidence-empty">
        <ShieldCheck className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No evidence spans available for this paper
        </p>
      </div>
    )
  }

  return (
    <div className="evidence-panel space-y-3 animate-fade-in">
      {spans.map((span) => {
        const v = verdictConfig[span.verdict]
        return (
          <div key={span.id} className="evidence-card">
            {/* Claim */}
            <div className="evidence-claim">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                {span.claim}
              </span>
            </div>

            {/* Verdict + confidence */}
            <div className="flex items-center gap-2">
              <span className={clsx('badge', v.color)}>
                {v.icon} {v.label}
              </span>
              <div className="flex items-center gap-1">
                <div className="w-12 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      'h-full rounded-full',
                      span.verdict === 'supports' && 'bg-green-500',
                      span.verdict === 'contradicts' && 'bg-red-500',
                      span.verdict === 'neutral' && 'bg-yellow-500',
                      span.verdict === 'insufficient' && 'bg-gray-400'
                    )}
                    style={{ width: `${Math.round(span.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {Math.round(span.confidence * 100)}%
                </span>
              </div>
            </div>

            {/* Evidence text */}
            <blockquote className="evidence-text">
              {span.evidence_text}
            </blockquote>

            {/* Context */}
            {span.context && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Context: {span.context}
              </p>
            )}

            {/* Meta */}
            <div className="evidence-meta">
              {span.section && <span>Section: {span.section}</span>}
              {span.page_number && <span>Page: {span.page_number}</span>}
              {span.llm_model && <span>Model: {span.llm_model}</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
