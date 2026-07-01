import { GitBranch, Database, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import type { QueryPlan as QueryPlanType } from '@/api/types'
import './QueryPlan.css'

const sourceColors: Record<string, string> = {
  semantic_scholar: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
  openalex: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
  crossref: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
  arxiv: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
}

interface QueryPlanProps {
  plan: QueryPlanType
  originalQuery?: string
}

export default function QueryPlan({ plan, originalQuery: _originalQuery }: QueryPlanProps) {
  const [expanded, setExpanded] = useState(false)

  if (!plan || !plan.sub_queries || plan.sub_queries.length === 0) return null

  return (
    <div className="query-plan card animate-fade-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="query-plan-header"
      >
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Query Plan
          </span>
          <span className="badge bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
            {plan.sub_queries.length} sub-queries
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="query-plan-body">
          <div className="query-plan-strategy">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Strategy
            </span>
            <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">{plan.strategy}</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {plan.intent && (
                <span className="badge bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
                  {plan.intent.split('_').join(' ')}
                </span>
              )}
              {Object.entries(plan.entities || {}).flatMap(([dimension, values]) =>
                values.slice(0, 3).map((value) => (
                  <span
                    key={`${dimension}-${value}`}
                    className="badge bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
                    title={dimension}
                  >
                    {value}
                  </span>
                ))
              )}
              {(plan.constraints || []).slice(0, 4).map((constraint, index) => (
                <span
                  key={`${constraint.key}-${index}`}
                  className="badge bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300"
                >
                  {constraint.key} {constraint.operator} {String(constraint.value)}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {plan.sub_queries.map((sq, i) => (
              <div
                key={i}
                className="query-plan-subquery"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Database className="w-3.5 h-3.5 text-gray-400" />
                  <span className={clsx('badge', sourceColors[sq.source] || 'bg-gray-100 text-gray-700')}>
                    {sq.source.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 font-mono">
                  {sq.query}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {sq.rationale}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
