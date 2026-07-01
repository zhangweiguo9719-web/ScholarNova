/**
 * 语言切换组件
 */

import { useLocaleStore } from '@/stores/localeStore'
import { Locale } from '@/i18n'

export default function LanguageSwitcher() {
  const { locale, setLocale } = useLocaleStore()

  const toggleLocale = () => {
    const newLocale: Locale = locale === 'zh' ? 'en' : 'zh'
    setLocale(newLocale)
  }

  return (
    <button
      onClick={toggleLocale}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
        bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700
        text-gray-700 dark:text-gray-300 transition-colors"
      title={locale === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      <span className="text-base">{locale === 'zh' ? '🇨🇳' : '🇺🇸'}</span>
      <span>{locale === 'zh' ? '中文' : 'EN'}</span>
    </button>
  )
}
