import { useLocaleStore } from '@/stores/localeStore'

export default function Footer() {
  const { t } = useLocaleStore()

  return (
    <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span>ScholarNova - {t('footer.poweredBy')}</span>
        <span>Semantic Scholar · OpenAlex · CrossRef · arXiv</span>
      </div>
    </footer>
  )
}
