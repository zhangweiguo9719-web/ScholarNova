/**
 * 语言状态管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Locale, t, Translations, translations } from '@/i18n'

interface LocaleState {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (path: string, params?: Record<string, string | number>) => string
  translations: Translations
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set, get) => ({
      locale: 'zh', // 默认中文

      setLocale: (locale: Locale) => {
        set({ locale, translations: translations[locale] })
      },

      t: (path: string, params?: Record<string, string | number>) => {
        return t(get().locale, path, params)
      },

      translations: translations['zh'],
    }),
    {
      name: 'scholar-locale',
      partialize: (state) => ({ locale: state.locale }),
    }
  )
)
