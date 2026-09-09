import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { AgentChatResponse } from '@/api/types'
import { useAssistantStore } from '@/stores/assistantStore'
import ResearchAssistant from '../ResearchAssistant'

const mocks = vi.hoisted(() => ({ chat: vi.fn(), zoteroStatus: vi.fn() }))
vi.mock('@/api/client', () => ({
  agentApi: { chat: mocks.chat },
  zoteroApi: { status: mocks.zoteroStatus },
}))
vi.mock('@/stores/localeStore', () => ({ useLocaleStore: () => ({ locale: 'zh' }) }))

const productHelp: AgentChatResponse = {
  answer: '我可以帮助你检索论文、阅读全文和整理知识库。',
  response_type: 'product_help',
  citations: [],
  tool_steps: [{ tool: 'product_help', status: 'completed', count: 1, detail: '内置使用指南' }],
  provider: null,
  model: null,
  prompt_tokens: 0,
  completion_tokens: 0,
  retrieval_tokens: 0,
  total_tokens: 0,
  retrieval_mode: 'bm25',
  inference_mode: 'none',
  verification_status: 'not_applicable',
  citation_coverage: 0,
  uncited_claim_count: 0,
  invalid_citation_ids: [],
  fallback_used: false,
  model_fallback_used: false,
  model_route: 'none',
  model_attempts: [],
  grounded: false,
  created_at: '2026-09-09T00:00:00Z',
}

beforeEach(() => {
  vi.resetAllMocks()
  mocks.chat.mockResolvedValue({ data: productHelp })
  mocks.zoteroStatus.mockResolvedValue({ data: { connected: true } })
  HTMLElement.prototype.scrollIntoView = vi.fn()
  localStorage.clear()
  useAssistantStore.setState({
    folders: [],
    conversations: [{
      id: 'guide-chat', folderId: null, title: '新对话', messages: [], createdAt: 1, updatedAt: 1,
    }],
    activeConversationId: 'guide-chat',
  })
})

afterEach(cleanup)

function expectProductGuide() {
  expect(screen.getByText('产品使用指南')).toBeInTheDocument()
  expect(screen.getByText('本回答来自 ScholarNova 内置使用指南，无需论文引用。')).toBeInTheDocument()
  expect(screen.queryByText('材料不足')).not.toBeInTheDocument()
  expect(screen.queryByText(/BM25/)).not.toBeInTheDocument()
  expect(screen.queryByText('本次没有可引用材料')).not.toBeInTheDocument()
  expect(screen.queryByText(/引用覆盖:/)).not.toBeInTheDocument()
}

it('renders a capability answer as product help without research-evidence warnings', async () => {
  render(<ResearchAssistant />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '你可以做什么' } })
  fireEvent.click(screen.getByRole('button', { name: '发送' }))

  expect(await screen.findByText(productHelp.answer)).toBeInTheDocument()
  expect(mocks.chat).toHaveBeenCalledWith(expect.objectContaining({ question: '你可以做什么' }))
  expectProductGuide()
})

it('preserves product-help type and display when persisted history is rehydrated', async () => {
  useAssistantStore.getState().appendMessage('guide-chat', {
    id: 'guide-answer', role: 'assistant', content: productHelp.answer, result: productHelp,
  })
  const storageKey = 'scholarnova-assistant-workspace-v2'
  const persisted = localStorage.getItem(storageKey)!
  expect(JSON.parse(persisted).state.conversations[0].messages[0].result.response_type).toBe('product_help')

  useAssistantStore.setState({ conversations: [], activeConversationId: '' })
  localStorage.setItem(storageKey, persisted)
  await useAssistantStore.persist.rehydrate()

  expect(useAssistantStore.getState().conversations[0].messages[0].result).toEqual(productHelp)
  render(<ResearchAssistant />)
  expect(await screen.findByText(productHelp.answer)).toBeInTheDocument()
  expectProductGuide()
  expect(mocks.chat).not.toHaveBeenCalled()
})
