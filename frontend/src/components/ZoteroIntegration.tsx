import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  BookOpenCheck,
  AlertCircle,
  Download,
  ExternalLink,
  Loader2,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  Network,
} from 'lucide-react'
import { zoteroApi } from '@/api/client'
import type {
  ZoteroCollection,
  ZoteroImportResult,
  ZoteroStatus,
} from '@/api/types'
import { useLocaleStore } from '@/stores/localeStore'

function apiMessage(error: unknown, fallback: string): string {
  const candidate = error as {
    response?: { data?: { detail?: string | { message?: string } } }
  }
  const detail = candidate.response?.data?.detail
  return typeof detail === 'string' ? detail : detail?.message || fallback
}

function apiCode(error: unknown): string | undefined {
  const candidate = error as {
    response?: { data?: { detail?: { code?: string } } }
  }
  return candidate.response?.data?.detail?.code
}

export default function ZoteroIntegration() {
  const { t } = useLocaleStore()
  const [status, setStatus] = useState<ZoteroStatus | null>(null)
  const [collections, setCollections] = useState<ZoteroCollection[]>([])
  const [collectionKey, setCollectionKey] = useState('')
  const [checking, setChecking] = useState(true)
  const [detectionCode, setDetectionCode] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<ZoteroImportResult | null>(null)
  const zoteroMajorVersion = Number.parseInt(status?.zotero_version || '', 10)

  const detect = useCallback(async (silent: boolean = false) => {
    setChecking(true)
    setResult(null)
    try {
      const statusResponse = await zoteroApi.status()
      setStatus(statusResponse.data)
      setDetectionCode(null)
      const collectionResponse = await zoteroApi.collections()
      setCollections(collectionResponse.data.items)
    } catch (error) {
      setStatus(null)
      setDetectionCode(apiCode(error) || 'zotero_unavailable')
      setCollections([])
      if (!silent) {
        toast.error(apiMessage(error, t('settings.zoteroNotFound')))
      }
    } finally {
      setChecking(false)
    }
  }, [t])

  useEffect(() => {
    void detect(true)
  }, [detect])

  const importItems = async () => {
    setImporting(true)
    setResult(null)
    try {
      const response = await zoteroApi.importItems(collectionKey || null, 50)
      setResult(response.data)
      toast.success(
        t('settings.zoteroImportSuccess', {
          created: response.data.created,
          updated: response.data.updated,
        })
      )
    } catch (error) {
      toast.error(apiMessage(error, t('settings.zoteroImportFailed')))
    } finally {
      setImporting(false)
    }
  }

  return (
    <section className="card overflow-hidden">
      <div className="border-b border-[var(--ui-border)] px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]">
              <BookOpenCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold text-[var(--ui-text)]">
                {t('settings.zoteroTitle')}
              </h2>
              <p className="mt-1 text-sm leading-6 text-[var(--ui-text-soft)]">
                {t('settings.zoteroDescription')}
              </p>
            </div>
          </div>
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[var(--ui-border)] px-2.5 py-1 text-xs text-[var(--ui-text-soft)]">
            <ShieldCheck className="h-3.5 w-3.5" />
            {t('settings.zoteroReadOnly')}
          </span>
        </div>
      </div>

      <div className="space-y-4 px-5 py-5">
        <div
          className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
            status?.connected
              ? 'border-emerald-500/25 bg-emerald-500/5'
              : 'border-amber-500/25 bg-amber-500/5'
          }`}
        >
          {checking ? (
            <Loader2 className="mt-0.5 h-5 w-5 animate-spin text-[var(--ui-accent)]" />
          ) : status?.connected ? (
            <ShieldCheck className="mt-0.5 h-5 w-5 text-emerald-500" />
          ) : (
            <AlertCircle className="mt-0.5 h-5 w-5 text-amber-500" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[var(--ui-text)]">
              {checking
                ? t('settings.zoteroChecking')
                : status?.connected
                  ? t('settings.zoteroConnected')
                  : detectionCode === 'zotero_api_disabled'
                    ? t('settings.zoteroApiDisabled')
                    : t('settings.zoteroNotFound')}
            </p>
            <p className="mt-1 text-xs leading-5 text-[var(--ui-text-soft)]">
              {status?.connected
                ? t('settings.zoteroConnectedHint', {
                    count: collections.length,
                  })
                : t('settings.zoteroEnableHint')}
            </p>
            {status?.zotero_version && (
              <p className="mt-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                {t('settings.zoteroVersion', { version: status.zotero_version })}
              </p>
            )}
            {status?.connected && Number.isFinite(zoteroMajorVersion) && zoteroMajorVersion < 10 && (
              <p className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs leading-5 text-amber-700 dark:text-amber-300">
                {t('settings.zoteroWriteUpgrade')}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => void detect(false)}
            disabled={checking}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--ui-border)] px-3 py-2 text-xs font-medium text-[var(--ui-text)] transition hover:border-[var(--ui-border-strong)] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} />
            {t('settings.zoteroDetect')}
          </button>
        </div>

        <details
          open={!status?.connected}
          className="group rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface-soft)]"
        >
          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold text-[var(--ui-text)]">
            <Network className="h-4 w-4 text-[var(--ui-accent)]" />
            {t('settings.zoteroSetupTitle')}
            <span className="ml-auto text-xs font-normal text-[var(--ui-muted)] group-open:hidden">
              {status?.connected ? '✓' : ''}
            </span>
          </summary>
          <div className="space-y-3 border-t border-[var(--ui-border)] px-4 py-4">
            {[
              t('settings.zoteroSetupStep1'),
              t('settings.zoteroSetupStep2'),
              t('settings.zoteroSetupStep3'),
            ].map((step, index) => (
              <div key={step} className="flex items-start gap-3 text-sm leading-6 text-[var(--ui-text-soft)]">
                {status?.connected ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                ) : (
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--ui-accent-soft)] text-[11px] font-bold text-[var(--ui-accent)]">
                    {index + 1}
                  </span>
                )}
                <span>{step}</span>
              </div>
            ))}
            <p className="rounded-lg border border-[var(--ui-border)] px-3 py-2 font-mono text-[11px] text-[var(--ui-muted)]">
              {t('settings.zoteroApiAddress')}
            </p>
          </div>
        </details>

        {status?.connected && (
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-[var(--ui-text-soft)]">
                {t('settings.zoteroCollection')}
              </span>
              <select
                value={collectionKey}
                onChange={(event) => setCollectionKey(event.target.value)}
                className="h-11 w-full rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface-solid)] px-3 text-sm text-[var(--ui-text)] outline-none transition focus:border-[var(--ui-border-strong)]"
              >
                <option value="">{t('settings.zoteroAllItems')}</option>
                {collections.map((collection) => (
                  <option key={collection.key} value={collection.key}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void importItems()}
              disabled={importing}
              className="mt-auto inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--ui-brand)] px-4 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60 dark:text-[#101722]"
            >
              {importing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              {importing
                ? t('settings.zoteroImporting')
                : t('settings.zoteroImport')}
            </button>
          </div>
        )}

        {result && (
          <div className="rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface-soft)] px-4 py-3 text-sm text-[var(--ui-text-soft)]">
            {t('settings.zoteroImportSummary', {
              total: result.total,
              created: result.created,
              updated: result.updated,
              skipped: result.skipped,
            })}
          </div>
        )}

        <a
          href="https://www.zotero.org/download/"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--ui-accent)] hover:underline"
        >
          {t('settings.zoteroDownload')}
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    </section>
  )
}
