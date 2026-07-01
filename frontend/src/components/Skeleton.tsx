import clsx from 'clsx'

interface SkeletonProps {
  className?: string
  lines?: number
  variant?: 'text' | 'card' | 'circle'
}

export default function Skeleton({ className, lines = 1, variant = 'text' }: SkeletonProps) {
  if (variant === 'circle') {
    return <div className={clsx('skeleton rounded-full', className)} />
  }

  if (variant === 'card') {
    return (
      <div className={clsx('card p-4 space-y-3', className)}>
        <div className="skeleton h-5 w-3/4" />
        <div className="skeleton h-4 w-1/2" />
        <div className="skeleton h-3 w-full" />
        <div className="skeleton h-3 w-5/6" />
        <div className="skeleton h-3 w-2/3" />
        <div className="flex gap-2 mt-2">
          <div className="skeleton h-5 w-16 rounded-full" />
          <div className="skeleton h-5 w-20 rounded-full" />
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-4"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  )
}

export function PaperCardSkeleton() {
  return (
    <div className="paper-card-skeleton space-y-3">
      <div className="skeleton-line" style={{ width: '80%' }} />
      <div className="skeleton-line" style={{ width: '50%', height: '0.75rem' }} />
      <div className="skeleton-line" style={{ width: '100%' }} />
      <div className="skeleton-line" style={{ width: '90%' }} />
      <div className="skeleton-line" style={{ width: '60%' }} />
      <div className="flex gap-2 mt-1">
        <div className="skeleton-line" style={{ width: '3rem', height: '1.25rem', borderRadius: '9999px' }} />
        <div className="skeleton-line" style={{ width: '4rem', height: '1.25rem', borderRadius: '9999px' }} />
        <div className="skeleton-line" style={{ width: '3rem', height: '1.25rem', borderRadius: '9999px' }} />
      </div>
    </div>
  )
}
