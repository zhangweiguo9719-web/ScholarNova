/** 搜索历史：localStorage 持久化，供首页/搜索页展示与回访。 */
const STORAGE_KEY = 'scholarnova-search-history'
const MAX_ITEMS = 10

export interface SearchHistoryItem {
  query: string
  at: number
}

export function getSearchHistory(): SearchHistoryItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter(
        (x: unknown): x is SearchHistoryItem =>
          !!x &&
          typeof x === 'object' &&
          typeof (x as SearchHistoryItem).query === 'string'
      )
      .slice(0, MAX_ITEMS)
  } catch {
    return []
  }
}

/** 记录一次搜索：去重置顶、限 10 条。返回更新后的历史。 */
export function addSearchHistory(query: string): SearchHistoryItem[] {
  const trimmed = (query || '').trim()
  if (!trimmed) return getSearchHistory()
  const rest = getSearchHistory().filter((item) => item.query !== trimmed)
  const next = [{ query: trimmed, at: Date.now() }, ...rest].slice(0, MAX_ITEMS)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    /* localStorage 不可用时静默降级 */
  }
  return next
}

export function clearSearchHistory(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
