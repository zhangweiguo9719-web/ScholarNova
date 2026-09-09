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

function expectNoResearchWarnings() {
  expect(screen.queryByText('材料不足')).not.toBeInTheDocument()
  expect(screen.queryByText(/BM25/)).not.toBeInTheDocument()
  expect(screen.queryByText('本次没有可引用材料')).not.toBeInTheDocument()
  expect(screen.queryByText(/引用覆盖:/)).not.toBeInTheDocument()
  expect(screen.queryByText('模型离线 · 证据回退')).not.toBeInTheDocument()
}

function expectProductGuide() {
  expect(screen.getByText('产品使用指南')).toBeInTheDocument()
  expect(screen.getByText('本回答来自 ScholarNova 内置使用指南，无需论文引用。')).toBeInTheDocument()
  expectNoResearchWarnings()
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

const primaryAttempt = {
  role: 'primary' as const, provider: 'guide-provider', model: 'guide-model', status: 'completed' as const,
  prompt_tokens: 100, completion_tokens: 23, total_tokens: 123, requests: 1, error_type: null,
}

const modelHelp: AgentChatResponse = {
  ...productHelp,
  inference_mode: 'model', model_route: 'primary', provider: 'guide-provider', model: 'guide-model',
  prompt_tokens: 100, completion_tokens: 23, total_tokens: 123, model_attempts: [primaryAttempt],
}

async function renderSavedAnswer(result: AgentChatResponse) {
  useAssistantStore.getState().appendMessage('guide-chat', {
    id: 'guide-answer', role: 'assistant', content: result.answer, result,
  })
  render(<ResearchAssistant />)
  expect(await screen.findByText(result.answer)).toBeInTheDocument()
}

it('labels model-generated help and displays its model and real token usage', async () => {
  await renderSavedAnswer(modelHelp)

  expect(screen.getByText('AI 使用指导')).toBeInTheDocument()
  expect(screen.getByText('模型: guide-provider/guide-model')).toBeInTheDocument()
  expect(screen.getByText('Token: 123')).toBeInTheDocument()
  expect(screen.getByText('模型尝试 1 次')).toHaveAttribute('title', expect.stringContaining('123 Token'))
  expect(screen.getByText(/本回答由已配置模型结合 ScholarNova 产品说明生成/)).toBeInTheDocument()
  expect(screen.queryByText(/本回答来自 ScholarNova 内置使用指南/)).not.toBeInTheDocument()
  expectNoResearchWarnings()
})

it('distinguishes fallback-model help from deterministic built-in help', async () => {
  await renderSavedAnswer({
    ...modelHelp,
    model_route: 'fallback', model_fallback_used: true, provider: 'backup-provider', model: 'backup-model',
    total_tokens: 175,
    model_attempts: [
      { ...primaryAttempt, status: 'unavailable', total_tokens: 52, error_type: 'TimeoutError' },
      { ...primaryAttempt, role: 'fallback', provider: 'backup-provider', model: 'backup-model' },
    ],
  })

  expect(screen.getByText('AI 使用指导 · 备用模型')).toBeInTheDocument()
  expect(screen.getByText('模型: backup-provider/backup-model')).toBeInTheDocument()
  expect(screen.getByText('Token: 175')).toBeInTheDocument()
  expect(screen.getByText('模型尝试 2 次')).toHaveAttribute('title', expect.stringContaining('unavailable'))
  expect(screen.queryByText('内置帮助兜底')).not.toBeInTheDocument()
  expectNoResearchWarnings()
})

it('reports built-in fallback without hiding tokens consumed by failed model attempts', async () => {
  await renderSavedAnswer({
    ...modelHelp,
    inference_mode: 'deterministic_fallback', model_route: 'deterministic', fallback_used: true,
    total_tokens: 17,
    model_attempts: [{ ...primaryAttempt, status: 'unavailable', total_tokens: 17, error_type: 'TimeoutError' }],
  })

  expect(screen.getByText('内置帮助兜底')).toBeInTheDocument()
  expect(screen.getByText(/模型未完成本次指导，已显示内置帮助/)).toBeInTheDocument()
  expect(screen.getByText('Token: 17')).toBeInTheDocument()
  expect(screen.getByText('模型尝试 1 次')).toHaveAttribute('title', expect.stringContaining('unavailable'))
  expect(screen.queryByText('模型: guide-provider/guide-model')).not.toBeInTheDocument()
  expect(screen.queryByText('AI 使用指导')).not.toBeInTheDocument()
  expectNoResearchWarnings()
})

it('sends only the active conversation\'s latest six messages for a follow-up', async () => {
  const previousMessages = Array.from({ length: 8 }, (_, index) => ({
    id: `message-${index}`, role: index % 2 ? 'assistant' as const : 'user' as const,
    content: `当前会话消息 ${index}`, ...(index % 2 ? { result: modelHelp } : {}),
  }))
  useAssistantStore.getState().replaceMessages('guide-chat', previousMessages)
  const otherChat = useAssistantStore.getState().createConversation()
  useAssistantStore.getState().appendMessage(otherChat, { id: 'other', role: 'user', content: '另一个会话的私有内容' })
  useAssistantStore.getState().setActiveConversation('guide-chat')
  render(<ResearchAssistant />)

  fireEvent.change(screen.getByRole('textbox'), { target: { value: '那怎样导入 PDF？' } })
  fireEvent.click(screen.getByRole('button', { name: '发送' }))
  expect(await screen.findByText(productHelp.answer)).toBeInTheDocument()

  expect(mocks.chat).toHaveBeenCalledOnce()
  expect(mocks.chat).toHaveBeenCalledWith({
    question: '那怎样导入 PDF？',
    history: previousMessages.slice(-6).map(({ role, content }) => ({ role, content })),
    use_knowledge: true,
    use_zotero: true,
  })
})
