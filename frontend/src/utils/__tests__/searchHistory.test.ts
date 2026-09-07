import { beforeEach, expect, it } from 'vitest'
import { addSearchHistory, getSearchHistory, clearSearchHistory } from '../searchHistory'

beforeEach(() => { localStorage.clear(); sessionStorage.clear() })

it('keeps recent queries within the window session and removes legacy persistence', () => {
  localStorage.setItem('scholarnova-search-history', JSON.stringify([{ query: 'old', at: 1 }]))
  expect(getSearchHistory()).toEqual([])
  addSearchHistory('traffic')
  expect(getSearchHistory()[0].query).toBe('traffic')
  expect(localStorage.getItem('scholarnova-search-history')).toBeNull()
  sessionStorage.clear()
  expect(getSearchHistory()).toEqual([])
})

it('clears recent queries explicitly', () => {
  addSearchHistory('traffic')
  clearSearchHistory()
  expect(getSearchHistory()).toEqual([])
})
