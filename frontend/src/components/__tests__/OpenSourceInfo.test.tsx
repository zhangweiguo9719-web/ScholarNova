import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import OpenSourceInfo from '../OpenSourceInfo'
import { useLocaleStore } from '@/stores/localeStore'
import { version } from '../../../package.json'

afterEach(() => { cleanup(); vi.restoreAllMocks(); useLocaleStore.getState().setLocale('zh') })

describe('open source notices', () => {
  it('exposes desktop offline notices and the exact version source download', () => {
    vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue('ScholarNova Electron/44.2.0')
    render(<OpenSourceInfo />)
    expect(screen.getByRole('link', { name: '许可证与第三方声明' }).getAttribute('href')).toBe('/legal/index.html')
    expect(screen.getByRole('link', { name: '下载本版本对应源码' }).getAttribute('href'))
      .toBe(`https://github.com/zhangweiguo9719-web/ScholarNova/releases/download/v${version}/ScholarNova-${version}-corresponding-source.zip`)
    expect(screen.getByText(/GNU AGPL v3/).textContent).toContain('不附带担保')
  })

  it('provides English web notices without advertising an unavailable local route', () => {
    vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue('Mozilla/5.0')
    useLocaleStore.getState().setLocale('en')
    render(<OpenSourceInfo />)
    expect(screen.getByRole('link', { name: 'Licenses and third-party notices' }).getAttribute('href'))
      .toContain('/blob/main/THIRD_PARTY_NOTICES.md')
    expect(screen.getByText(/GNU AGPL v3/).textContent).toContain('without warranty')
  })
})
