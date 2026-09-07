import { act, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { useSearchStore } from '@/stores/searchStore'
import Search from '../Search'

const api = vi.hoisted(() => ({ create: vi.fn(), getRun: vi.fn(), get: vi.fn(), analyze: vi.fn() }))
const uploadCallback = vi.hoisted(() => ({ current: () => {} }))
vi.mock('@/api/client', () => ({
  searchApi: { create: api.create, getRun: api.getRun },
  papersApi: { get: api.get, analyze: api.analyze },
  networkApi: {},
}))
vi.mock('@/components/QueryPlan/QueryPlan', () => ({ default: () => null }))
vi.mock('@/components/SearchInsights/SearchInsights', () => ({ default: () => null }))
vi.mock('@/components/ResultsList/ResultsList', () => ({
  default: ({ onPaperClick }: any) => <div>
    <button onClick={() => onPaperClick({ id: 'a', title: 'Paper A' })}>Paper A</button>
    <button onClick={() => onPaperClick({ id: 'b', title: 'Paper B' })}>Paper B</button>
  </div>,
}))
vi.mock('@/components/PaperDetail/PaperDetail', () => ({
  default: ({ paper, onFulltextUploaded }: any) => {
    uploadCallback.current = onFulltextUploaded
    return <div data-testid="detail">{paper.id}</div>
  },
}))

beforeEach(() => {
  vi.resetAllMocks()
  useSearchStore.getState().clearSearch()
  api.create.mockResolvedValue({ data: { run_id: 'run' } })
  api.getRun.mockResolvedValue({ data: { run_id: 'run', status: 'completed', results: [{ id: 'a' }], query: 'traffic' } })
})

it('does not restore a search when its creation finishes after leaving the page', async () => {
  let finish!: (value: any) => void
  api.create.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const view = render(<MemoryRouter initialEntries={['/search?q=traffic']}><Search /></MemoryRouter>)
  await waitFor(() => expect(api.create).toHaveBeenCalledOnce())
  view.unmount()
  await act(async () => { finish({ data: { run_id: 'stale' } }) })
  expect(api.getRun).not.toHaveBeenCalled()
  expect(useSearchStore.getState().searchRun).toBeNull()
  expect(useSearchStore.getState().isLoading).toBe(false)
})

it('keeps the latest selected paper when detail responses arrive out of order', async () => {
  let finishA!: (value: any) => void
  api.get.mockImplementation((id: string) => id === 'a'
    ? new Promise(resolve => { finishA = resolve })
    : Promise.resolve({ data: { id: 'b' } }))
  const view = render(<MemoryRouter initialEntries={['/search?q=traffic']}><Search /></MemoryRouter>)
  fireEvent.click(await screen.findByText('Paper A'))
  fireEvent.click(screen.getByText('Paper B'))
  await waitFor(() => expect(screen.getByTestId('detail').textContent).toBe('b'))
  await act(async () => { finishA({ data: { id: 'a' } }) })
  expect(screen.getByTestId('detail').textContent).toBe('b')
  view.unmount()
})

it('ignores a pending PDF-upload callback after leaving its search session', async () => {
  api.get.mockResolvedValue({ data: { id: 'a' } })
  const view = render(<MemoryRouter initialEntries={['/search?q=traffic']}><Search /></MemoryRouter>)
  fireEvent.click(await screen.findByText('Paper A'))
  await screen.findByTestId('detail')
  const finishUpload = uploadCallback.current
  view.unmount()
  act(() => finishUpload())
  expect(api.analyze).not.toHaveBeenCalled()
  expect(useSearchStore.getState().analysisLoading).toBe(false)
})
