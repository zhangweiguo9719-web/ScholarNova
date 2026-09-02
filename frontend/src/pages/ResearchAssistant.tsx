import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  Bot,
  BookMarked,
  CheckCircle2,
  Database,
  Eraser,
  ExternalLink,
  Folder,
  FolderPlus,
  Library,
  Loader2,
  MessageSquarePlus,
  Send,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
  Trash2,
} from 'lucide-react'
import { agentApi, zoteroApi } from '@/api/client'
import type { AgentChatResponse, AgentMessage } from '@/api/types'
import { useAssistantStore, type AssistantMessage } from '@/stores/assistantStore'
import { useLocaleStore } from '@/stores/localeStore'

const STORAGE_KEY = 'scholarnova-research-assistant-v1'

function newId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`
}

export default function ResearchAssistant() {
  const { locale } = useLocaleStore()
  const isChinese = locale === 'zh'
  const {
    folders,
    conversations,
    activeConversationId,
    createFolder,
    deleteFolder,
    createConversation,
    deleteConversation,
    setActiveConversation,
    moveConversation,
    appendMessage,
    replaceMessages,
    clearConversation: clearStoredConversation,
  } = useAssistantStore()
  const activeConversation = conversations.find((item) => item.id === activeConversationId) || conversations[0]
  const messages = activeConversation?.messages || []
  const [question, setQuestion] = useState('')
  const [showFolderInput, setShowFolderInput] = useState(false)
  const [folderName, setFolderName] = useState('')
  const [useKnowledge, setUseKnowledge] = useState(true)
  const [useZotero, setUseZotero] = useState(true)
  const [zoteroConnected, setZoteroConnected] = useState<boolean | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const copy = useMemo(() => isChinese ? {
    eyebrow: 'ScholarNova Research Copilot',
    title: '可追溯科研问答智能体',
    subtitle: '自动检索个人知识库与本机 Zotero，只依据找到的材料回答，并保留来源编号。',
    prototype: '智能体 MVP',
    knowledge: 'ScholarNova 知识库',
    zotero: '本机 Zotero',
    connected: '已连接',
    unavailable: '未连接',
    detecting: '检测中',
    emptyTitle: '从一个研究问题开始',
    emptyDesc: '智能体会先执行本地资料检索，再调用你配置的模型组织回答。它不会自动修改 Zotero。',
    placeholder: '例如：现有材料对联邦学习中的隐私风险形成了哪些共识？',
    send: '发送',
    clear: '清空对话',
    folders: '研究文件夹',
    unfiled: '未分类',
    newFolder: '新建文件夹',
    newChat: '新对话',
    folderPlaceholder: '例如：交通预测',
    moveTo: '所属文件夹',
    deleteFolder: '删除文件夹（对话移至未分类）',
    deleteChat: '删除当前对话',
    contextNotice: '每个对话使用独立上下文',
    tools: '工具执行',
    sources: '引用材料',
    noSource: '本次没有可引用材料',
    grounded: '基于本地材料',
    notGrounded: '材料不足',
    verified: '引用校验通过',
    partial: '引用覆盖不完整',
    verificationFailed: '引用校验失败',
    fallback: '模型离线 · 证据回退',
    modelFallback: '主模型异常 · 备用模型接管',
    coverage: '引用覆盖',
    uncited: '未引用事实句',
    productHelp: '产品使用指南',
    productHelpSource: '本回答来自 ScholarNova 内置使用指南，无需论文引用。',
    model: '模型',
    tokens: 'Token',
    retrieval: '检索',
    embeddingTokens: '向量 Token',
    safety: '回答是研究辅助信息，请回到原始论文核验关键结论。',
    examples: [
      '总结知识库中的主要研究空白',
      '比较 Zotero 文献中常见的方法路线',
      '基于现有材料提出三个可验证的研究问题',
    ],
  } : {
    eyebrow: 'ScholarNova Research Copilot',
    title: 'Traceable Research Assistant',
    subtitle: 'Searches your knowledge base and local Zotero library, answers only from retrieved material, and keeps source markers.',
    prototype: 'Agent MVP',
    knowledge: 'ScholarNova knowledge',
    zotero: 'Local Zotero',
    connected: 'Connected',
    unavailable: 'Unavailable',
    detecting: 'Detecting',
    emptyTitle: 'Start with a research question',
    emptyDesc: 'The assistant retrieves local evidence before calling your configured model. It never modifies Zotero automatically.',
    placeholder: 'For example: What consensus do my sources show about privacy risks in federated learning?',
    send: 'Send',
    clear: 'Clear conversation',
    folders: 'Research folders',
    unfiled: 'Unfiled',
    newFolder: 'New folder',
    newChat: 'New chat',
    folderPlaceholder: 'For example: Traffic forecasting',
    moveTo: 'Folder',
    deleteFolder: 'Delete folder (chats move to Unfiled)',
    deleteChat: 'Delete current chat',
    contextNotice: 'Each chat has isolated context',
    tools: 'Tool activity',
    sources: 'Sources',
    noSource: 'No citable local material was found',
    grounded: 'Grounded locally',
    notGrounded: 'Insufficient material',
    verified: 'Citation checks passed',
    partial: 'Partial citation coverage',
    verificationFailed: 'Citation checks failed',
    fallback: 'Model offline · evidence fallback',
    modelFallback: 'Primary unavailable · fallback model used',
    coverage: 'Citation coverage',
    uncited: 'Uncited factual segments',
    productHelp: 'Product guide',
    productHelpSource: 'This response comes from the built-in ScholarNova guide and does not require paper citations.',
    model: 'Model',
    tokens: 'Tokens',
    retrieval: 'Retrieval',
    embeddingTokens: 'Embedding tokens',
    safety: 'This is research assistance. Verify important claims against the original papers.',
    examples: [
      'Summarize the main research gaps in my knowledge base',
      'Compare common methods in my Zotero literature',
      'Propose three testable questions from my current evidence',
    ],
  }, [isChinese])

  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  useEffect(() => {
    if (!activeConversation || activeConversation.messages.length > 0) return
    try {
      const legacy = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
      if (Array.isArray(legacy) && legacy.length > 0) {
        replaceMessages(activeConversation.id, legacy.slice(-40) as AssistantMessage[])
      }
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [activeConversation?.id, replaceMessages])

  useEffect(() => {
    let active = true
    void zoteroApi.status()
      .then(() => active && setZoteroConnected(true))
      .catch(() => active && setZoteroConnected(false))
    return () => { active = false }
  }, [])

  const submit = async () => {
    const cleanQuestion = question.trim()
    if (!cleanQuestion || sending || !activeConversation) return
    const conversationId = activeConversation.id
    const history: AgentMessage[] = messages.slice(-6).map(({ role, content }) => ({ role, content }))
    const userEntry: AssistantMessage = { id: newId(), role: 'user', content: cleanQuestion }
    appendMessage(conversationId, userEntry)
    setQuestion('')
    setError('')
    setSending(true)
    try {
      const response = await agentApi.chat({
        question: cleanQuestion,
        history,
        use_knowledge: useKnowledge,
        use_zotero: useZotero,
      })
      appendMessage(conversationId, {
        id: newId(),
        role: 'assistant',
        content: response.data.answer,
        result: response.data,
      })
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail
        || (isChinese ? '智能体暂时无法回答，请检查模型和 Zotero 设置。' : 'The assistant could not answer. Check model and Zotero settings.')
      )
    } finally {
      setSending(false)
    }
  }

  const clearConversation = () => {
    if (activeConversation) clearStoredConversation(activeConversation.id)
    setError('')
    requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
  }

  const submitFolder = () => {
    const name = folderName.trim()
    if (!name) return
    const folderId = createFolder(name)
    createConversation(folderId)
    setFolderName('')
    setShowFolderInput(false)
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] bg-[var(--ui-canvas)] px-4 py-7 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <section className="relative overflow-hidden rounded-[1.4rem] border border-[var(--ui-border)] bg-[var(--ui-surface)] p-6 shadow-[var(--ui-shadow)] sm:p-8">
          <div className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-[var(--ui-glow)] blur-3xl" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ui-accent)]">{copy.eyebrow}</span>
                <span className="rounded-full border border-[var(--ui-border-strong)] bg-[var(--ui-accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--ui-accent)]">{copy.prototype}</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--ui-text)] sm:text-3xl">{copy.title}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--ui-text-soft)]">{copy.subtitle}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <SourceToggle active={useKnowledge} onClick={() => setUseKnowledge((value) => !value)} icon={<BookMarked className="h-4 w-4" />} label={copy.knowledge} />
              <SourceToggle active={useZotero} onClick={() => setUseZotero((value) => !value)} icon={<Library className="h-4 w-4" />} label={`${copy.zotero} · ${zoteroConnected === null ? copy.detecting : zoteroConnected ? copy.connected : copy.unavailable}`} warning={zoteroConnected === false} />
            </div>
          </div>
        </section>

        <section className="card mt-5 overflow-hidden">
          <div className="flex min-h-[560px] flex-col md:flex-row">
            <aside className="border-b border-[var(--ui-border)] bg-[var(--ui-surface-raised)] p-3 md:w-64 md:shrink-0 md:border-b-0 md:border-r">
              <div className="flex items-center justify-between gap-2 px-1 pb-3">
                <div>
                  <p className="text-xs font-bold text-[var(--ui-text)]">{copy.folders}</p>
                  <p className="mt-0.5 text-[10px] text-[var(--ui-muted)]">{copy.contextNotice}</p>
                </div>
                <div className="flex gap-1">
                  <button title={copy.newFolder} onClick={() => setShowFolderInput((value) => !value)} className="rounded-lg p-2 text-[var(--ui-text-soft)] hover:bg-[var(--ui-accent-soft)] hover:text-[var(--ui-accent)]"><FolderPlus className="h-4 w-4" /></button>
                  <button title={copy.newChat} onClick={() => createConversation(activeConversation?.folderId || null)} className="rounded-lg p-2 text-[var(--ui-text-soft)] hover:bg-[var(--ui-accent-soft)] hover:text-[var(--ui-accent)]"><MessageSquarePlus className="h-4 w-4" /></button>
                </div>
              </div>

              {showFolderInput && (
                <div className="mb-3 flex gap-1.5">
                  <input autoFocus value={folderName} maxLength={40} placeholder={copy.folderPlaceholder} onChange={(event) => setFolderName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') submitFolder() }} className="min-w-0 flex-1 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-surface-solid)] px-2.5 py-2 text-xs text-[var(--ui-text)] outline-none focus:border-[var(--ui-border-strong)]" />
                  <button onClick={submitFolder} disabled={!folderName.trim()} className="rounded-lg bg-[var(--ui-brand)] px-2.5 text-xs font-bold text-white disabled:opacity-40 dark:text-[#101722]">+</button>
                </div>
              )}

              <div className="custom-scrollbar max-h-48 space-y-3 overflow-y-auto pr-1 md:max-h-[470px]">
                {[{ id: null, name: copy.unfiled }, ...folders].map((folder) => {
                  const chats = conversations.filter((conversation) => conversation.folderId === folder.id)
                  return (
                    <div key={folder.id || 'unfiled'}>
                      <div className="mb-1 flex items-center gap-1.5 px-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--ui-muted)]">
                        <Folder className="h-3.5 w-3.5" />
                        <span className="min-w-0 flex-1 truncate">{folder.name}</span>
                        {folder.id && <button title={copy.deleteFolder} onClick={() => deleteFolder(folder.id!)} className="rounded p-1 hover:bg-red-500/10 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>}
                      </div>
                      <div className="space-y-1">
                        {chats.map((conversation) => (
                          <button key={conversation.id} onClick={() => setActiveConversation(conversation.id)} className={`group flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${conversation.id === activeConversation?.id ? 'bg-[var(--ui-accent-soft)] font-semibold text-[var(--ui-text)]' : 'text-[var(--ui-text-soft)] hover:bg-[var(--ui-surface-soft)] hover:text-[var(--ui-text)]'}`}>
                            <Bot className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate">{conversation.title === '新对话' ? copy.newChat : conversation.title}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </aside>

            <div className="flex min-w-0 flex-1 flex-col">
              {activeConversation && (
                <div className="flex flex-wrap items-center gap-2 border-b border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-3">
                  <p className="min-w-0 flex-1 truncate text-sm font-semibold text-[var(--ui-text)]">{activeConversation.title === '新对话' ? copy.newChat : activeConversation.title}</p>
                  <label className="flex items-center gap-2 text-[11px] text-[var(--ui-muted)]">
                    {copy.moveTo}
                    <select value={activeConversation.folderId || ''} onChange={(event) => moveConversation(activeConversation.id, event.target.value || null)} className="rounded-lg border border-[var(--ui-border)] bg-[var(--ui-surface-solid)] px-2 py-1.5 text-xs text-[var(--ui-text)] outline-none">
                      <option value="">{copy.unfiled}</option>
                      {folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}
                    </select>
                  </label>
                  <button title={copy.deleteChat} onClick={() => deleteConversation(activeConversation.id)} className="rounded-lg p-2 text-[var(--ui-muted)] hover:bg-red-500/10 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
              )}

              <div className="custom-scrollbar max-h-[560px] flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-7">
              {messages.length === 0 && (
                <div className="mx-auto flex max-w-2xl flex-col items-center py-12 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]"><Bot className="h-7 w-7" /></div>
                  <h2 className="mt-5 text-lg font-bold text-[var(--ui-text)]">{copy.emptyTitle}</h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--ui-text-soft)]">{copy.emptyDesc}</p>
                  <div className="mt-6 grid w-full gap-2 sm:grid-cols-3">
                    {copy.examples.map((example) => (
                      <button key={example} onClick={() => setQuestion(example)} className="rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface-soft)] px-3 py-3 text-left text-xs leading-5 text-[var(--ui-text-soft)] transition hover:border-[var(--ui-border-strong)] hover:text-[var(--ui-text)]">{example}</button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <article key={message.id} className={message.role === 'user' ? 'ml-auto max-w-3xl' : 'mr-auto max-w-4xl'}>
                  <div className={`rounded-2xl px-4 py-3 text-sm leading-7 ${message.role === 'user' ? 'bg-[var(--ui-brand)] text-white dark:text-[#101722]' : 'border border-[var(--ui-border)] bg-[var(--ui-surface-soft)] text-[var(--ui-text)]'}`}>
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  </div>
                  {message.result && <AgentTrace result={message.result} copy={copy} isChinese={isChinese} />}
                </article>
              ))}

              {sending && (
                <div className="flex items-center gap-3 text-sm text-[var(--ui-text-soft)]">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--ui-accent)]" />
                  {isChinese ? '正在检索本地材料并组织回答…' : 'Retrieving local evidence and composing an answer…'}
                </div>
              )}
              <div ref={bottomRef} />
              </div>

              <div className="border-t border-[var(--ui-border)] bg-[var(--ui-surface-raised)] p-4 sm:p-5">
              {error && <div className="mb-3 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600 dark:text-red-400"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
              <div className="flex items-end gap-3">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      void submit()
                    }
                  }}
                  rows={2}
                  maxLength={2000}
                  placeholder={copy.placeholder}
                  className="min-h-[60px] flex-1 resize-none rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface-solid)] px-4 py-3 text-sm leading-6 text-[var(--ui-text)] outline-none transition placeholder:text-[var(--ui-muted)] focus:border-[var(--ui-border-strong)] focus:ring-4 focus:ring-[var(--ui-ring)]"
                />
                <button onClick={() => void submit()} disabled={!question.trim() || sending} className="inline-flex h-[60px] items-center justify-center gap-2 rounded-2xl bg-[var(--ui-brand)] px-5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-45 dark:text-[#101722]">
                  {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  <span className="hidden sm:inline">{copy.send}</span>
                </button>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-[var(--ui-muted)]">
                <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" />{copy.safety}</span>
                {messages.length > 0 && <button onClick={clearConversation} className="inline-flex shrink-0 items-center gap-1 hover:text-[var(--ui-text)]"><Eraser className="h-3.5 w-3.5" />{copy.clear}</button>}
              </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function SourceToggle({ active, onClick, icon, label, warning = false }: { active: boolean; onClick: () => void; icon: ReactNode; label: string; warning?: boolean }) {
  return (
    <button onClick={onClick} aria-pressed={active} className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition ${active ? 'border-[var(--ui-border-strong)] bg-[var(--ui-accent-soft)] text-[var(--ui-text)]' : 'border-[var(--ui-border)] text-[var(--ui-muted)]'} ${warning ? 'border-amber-500/25' : ''}`}>
      {icon}{label}{active && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />}
    </button>
  )
}

function AgentTrace({ result, copy, isChinese }: { result: AgentChatResponse; copy: Record<string, any>; isChinese: boolean }) {
  const isProductHelp = result.response_type === 'product_help'
  const verificationStatus = result.verification_status || (result.grounded ? 'verified' : 'not_applicable')
  const statusLabel = result.fallback_used
    ? copy.fallback
    : result.model_fallback_used
      ? copy.modelFallback
    : verificationStatus === 'verified'
      ? copy.verified
      : verificationStatus === 'partial'
        ? copy.partial
        : verificationStatus === 'failed'
          ? copy.verificationFailed
          : copy.notGrounded
  const statusStyle = verificationStatus === 'verified'
    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
    : verificationStatus === 'failed'
      ? 'bg-red-500/10 text-red-600 dark:text-red-400'
      : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
  return (
    <div className="mt-3 space-y-3 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-3 text-xs text-[var(--ui-text-soft)]">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-semibold ${isProductHelp ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400' : statusStyle}`}>
          {isProductHelp ? <Bot className="h-3.5 w-3.5" /> : verificationStatus === 'verified' ? <ShieldCheck className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
          {isProductHelp ? copy.productHelp : statusLabel}
        </span>
        {result.model && <span>{copy.model}: {result.provider}/{result.model}</span>}
        {result.model_attempts?.length > 1 && (
          <span title={result.model_attempts.map((attempt) => `${attempt.role}: ${attempt.provider}/${attempt.model} · ${attempt.status} · ${attempt.total_tokens} Token`).join('\n')}>
            {isChinese ? `模型尝试 ${result.model_attempts.length} 次` : `${result.model_attempts.length} model attempts`}
          </span>
        )}
        {!isProductHelp && <span>{copy.retrieval}: {result.retrieval_mode === 'hybrid' ? 'BM25 + Embedding RRF' : 'BM25'}</span>}
        {result.retrieval_tokens > 0 && <span>{copy.embeddingTokens}: {result.retrieval_tokens}</span>}
        {!isProductHelp && verificationStatus !== 'not_applicable' && <span>{copy.coverage}: {Math.round((result.citation_coverage || 0) * 100)}%</span>}
        <span>{copy.tokens}: {result.total_tokens}</span>
      </div>
      {!isProductHelp && (verificationStatus === 'partial' || verificationStatus === 'failed') && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-2.5 py-2 text-amber-700 dark:text-amber-300">
          {copy.uncited}: {result.uncited_claim_count || 0}
          {result.invalid_citation_ids?.length > 0 && ` · ${isChinese ? '无效编号' : 'Invalid IDs'}: ${result.invalid_citation_ids.join(', ')}`}
        </div>
      )}
      <div>
        <p className="mb-2 inline-flex items-center gap-1 font-semibold text-[var(--ui-text)]"><Sparkles className="h-3.5 w-3.5 text-[var(--ui-accent)]" />{copy.tools}</p>
        <div className="flex flex-wrap gap-2">
          {result.tool_steps.map((step) => (
            <span key={step.tool} title={step.detail} className="rounded-lg border border-[var(--ui-border)] bg-[var(--ui-surface-soft)] px-2 py-1.5">
              {step.tool} · {step.status}{step.count ? ` · ${step.count}` : ''}
            </span>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 inline-flex items-center gap-1 font-semibold text-[var(--ui-text)]"><Database className="h-3.5 w-3.5 text-[var(--ui-accent)]" />{copy.sources}</p>
        {result.citations.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {result.citations.map((citation) => {
              const safeUrl = /^https?:\/\//i.test(citation.url || '') ? citation.url : null
              const location = citation.source === 'paper'
                ? [citation.section, citation.page ? (isChinese ? `第 ${citation.page} 页` : `p. ${citation.page}`) : null].filter(Boolean).join(' · ')
                : citation.source === 'knowledge' && citation.chunk_index
                  ? (isChinese ? `知识片段 ${citation.chunk_index}` : `Knowledge chunk ${citation.chunk_index}`)
                  : citation.source === 'zotero'
                    ? (isChinese ? 'Zotero 元数据与摘要' : 'Zotero metadata and abstract')
                    : ''
              return <div key={citation.id} className="rounded-lg border border-[var(--ui-border)] px-2.5 py-2">
                <div className="flex items-start gap-2">
                  <span className="font-mono font-bold text-[var(--ui-accent)]">[{citation.id}]</span>
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 font-medium text-[var(--ui-text)]">{citation.title}</p>
                    <p className="mt-1 uppercase tracking-wide text-[10px] text-[var(--ui-muted)]">{citation.source}</p>
                    {location && <p className="mt-1 text-[11px] text-[var(--ui-text-soft)]">{location}</p>}
                  </div>
                  {safeUrl && <a href={safeUrl} target="_blank" rel="noreferrer" aria-label={citation.title}><ExternalLink className="h-3.5 w-3.5" /></a>}
                </div>
              </div>
            })}
          </div>
        ) : <p>{isProductHelp ? copy.productHelpSource : copy.noSource}</p>}
      </div>
    </div>
  )
}
