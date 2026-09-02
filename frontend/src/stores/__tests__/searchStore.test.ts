import { beforeEach, describe, expect, it } from 'vitest'
import { useSearchStore } from '@/stores/searchStore'

describe('search session store', () => {
  beforeEach(() => {
    localStorage.clear()
    useSearchStore.getState().clearSearch()
  })

  it('clears all page-scoped search and analysis state', () => {
    const store = useSearchStore.getState()
    store.setQuery('graph neural networks')
    store.setIsLoading(true)
    store.setAnalysisLoading(true)
    store.setEvidenceLoading(true)

    useSearchStore.getState().clearSearch()

    const cleared = useSearchStore.getState()
    expect(cleared.query).toBe('')
    expect(cleared.isLoading).toBe(false)
    expect(cleared.analysisLoading).toBe(false)
    expect(cleared.evidenceLoading).toBe(false)
    expect(localStorage.getItem('scholar-search-state')).toBeNull()
  })
})
