import { useNavigate } from 'react-router-dom'
import { GitBranch, Globe, ShieldCheck, Sparkles } from 'lucide-react'
import SearchBar from '@/components/SearchBar/SearchBar'
import { useLocaleStore } from '@/stores/localeStore'

export default function Home() {
  const navigate = useNavigate()
  const { t, locale } = useLocaleStore()

  const handleSearch = (query: string) => {
    navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  const examples = locale === 'zh'
    ? [
        '联邦学习在医疗数据中的应用',
        'Transformer 注意力机制',
        'CRISPR 基因编辑应用',
      ]
    : [
        'transformer attention mechanism',
        'CRISPR gene editing applications',
        'reinforcement learning robotics',
      ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="text-center mb-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            {t('home.badge')}
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-gray-50 mb-4 leading-tight">
            {t('home.title')}<br />
            <span className="text-primary-600 dark:text-primary-400">{t('home.titleHighlight')}</span>
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
            {t('home.subtitle')}
          </p>
          <div className="max-w-xl mx-auto">
            <SearchBar size="lg" onSubmit={handleSearch} placeholder={t('home.searchPlaceholder')} />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 mt-4 text-xs text-gray-400 dark:text-gray-500">
            <span>{t('home.tryExamples')}</span>
            {examples.map((example) => (
              <button
                key={example}
                onClick={() => handleSearch(example)}
                className="px-2.5 py-1 rounded-full border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-4 pb-16">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={GitBranch}
            title={t('home.features.smartQuery.title')}
            description={t('home.features.smartQuery.desc')}
          />
          <FeatureCard
            icon={Globe}
            title={t('home.features.multiSource.title')}
            description={t('home.features.multiSource.desc')}
          />
          <FeatureCard
            icon={ShieldCheck}
            title={t('home.features.evidence.title')}
            description={t('home.features.evidence.desc')}
          />
        </div>
      </section>

      {/* Stats / trust */}
      <section className="px-4 pb-12">
        <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-center gap-8 text-center">
          <div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">4</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">{t('home.stats.sources')}</div>
          </div>
          <div className="w-px h-8 bg-gray-200 dark:bg-gray-700" />
          <div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">200M+</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">{t('home.stats.papers')}</div>
          </div>
          <div className="w-px h-8 bg-gray-200 dark:bg-gray-700" />
          <div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">AI</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">{t('home.stats.analysis')}</div>
          </div>
        </div>
      </section>
    </div>
  )
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}) {
  return (
    <div className="card p-6 hover:shadow-md transition-shadow">
      <div className="w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center mb-4">
        <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{description}</p>
    </div>
  )
}
