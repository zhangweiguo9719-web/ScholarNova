import { Link, useLocation } from 'react-router-dom'
import { BookOpen, Search, Settings, Moon, Sun, BookMarked } from 'lucide-react'
import { useState, useEffect } from 'react'
import clsx from 'clsx'
import { useLocaleStore } from '@/stores/localeStore'
import LanguageSwitcher from '@/components/LanguageSwitcher'

export default function Header() {
  const location = useLocation()
  const { t } = useLocaleStore()
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark' ||
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
    }
    return false
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [dark])

  const navItems = [
    { to: '/', label: t('nav.home'), icon: BookOpen },
    { to: '/search', label: t('nav.search'), icon: Search },
    { to: '/knowledge', label: t('nav.knowledge') || '知识库', icon: BookMarked },
    { to: '/settings', label: t('nav.settings'), icon: Settings },
  ]

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-primary-600 dark:text-primary-400 font-bold text-lg">
          <BookOpen className="w-6 h-6" />
          <span>ScholarNova</span>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {navItems.map(({ to, label, icon: Icon }) => {
            const isActive = location.pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            )
          })}

          {/* Language switcher */}
          <LanguageSwitcher />

          {/* Dark mode toggle */}
          <button
            onClick={() => setDark(!dark)}
            className="ml-2 p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Toggle dark mode"
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </nav>
      </div>
    </header>
  )
}
