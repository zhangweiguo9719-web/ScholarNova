import { version } from '../../package.json'
import { useLocaleStore } from '@/stores/localeStore'

const repository = 'https://github.com/zhangweiguo9719-web/ScholarNova'

export default function OpenSourceInfo() {
  const zh = useLocaleStore((state) => state.locale) === 'zh'
  const desktop = navigator.userAgent.includes('Electron/')
  return (
    <section aria-labelledby="open-source-title" className="mt-6 rounded-xl border border-gray-200 bg-white p-5 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
      <h2 id="open-source-title" className="font-semibold text-gray-900 dark:text-gray-100">
        ScholarNova {version} · {zh ? '开源许可与源码' : 'Licenses and source'}
      </h2>
      <p className="mt-3 leading-relaxed">
        {zh
          ? '© 2026 Zhang Weiguo and ScholarNova contributors。包含 PyMuPDF 的完整桌面组合按 GNU AGPL v3 条款发行，项目自有源码保留 MIT 声明。你可以在相应许可条件下使用、修改和再分发；软件按原样提供，不附带担保。第三方组件保留各自版权和条款。'
          : '© 2026 Zhang Weiguo and ScholarNova contributors. The combined desktop distribution containing PyMuPDF is provided under GNU AGPL v3; project-owned source retains its MIT notice. You may use, modify and redistribute under the applicable terms. Provided as-is, without warranty. Third-party components retain their own copyrights and terms.'}
      </p>
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
        <a className="underline underline-offset-4" href={desktop ? '/legal/index.html' : `${repository}/blob/main/THIRD_PARTY_NOTICES.md`} target="_blank" rel="noopener noreferrer">
          {zh ? '许可证与第三方声明' : 'Licenses and third-party notices'}
        </a>
        <a className="underline underline-offset-4" href={`${repository}/releases/download/v${version}/ScholarNova-${version}-corresponding-source.zip`} target="_blank" rel="noopener noreferrer">
          {zh ? '下载本版本对应源码' : 'Download corresponding source'}
        </a>
        <a className="underline underline-offset-4" href={`${repository}/tree/v${version}`} target="_blank" rel="noopener noreferrer">
          {zh ? '查看版本代码' : 'Browse version source'}
        </a>
      </div>
    </section>
  )
}
