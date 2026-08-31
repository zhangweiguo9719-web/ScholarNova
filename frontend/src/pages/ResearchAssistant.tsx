import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  Bot,
  BookMarked,
  CheckCircle2,
  Database,
  Eraser,
  ExternalLink,
  Library,
  Loader2,
  Send,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
} from 'lucide-react'
import { agentApi, zoteroApi } from '@/api/client'
import type { AgentChatResponse, AgentMessage } from '@/api/types'
import { useLocaleStore } from '@/stores/localeStore'

const STORAGE_KEY = 'scholarnova-research-assistant-v1'

interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  result?: AgentChatResponse
}

function newId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`
}

function loadConversation(): ChatEntry[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(parsed) ? parsed.slice(-16) : []
  } catch {
    return []
  }
}

export default function ResearchAssistant() {
  const { locale } = useLocaleStore()
  const isChinese = locale === 'zh'
  const [messages, setMessages] = useState<ChatEntry[]>(loadConversation)
  const [question, setQuestion] = useState('')
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
    tools: '工具执行',
    sources: '引用材料',
    noSource: '本次没有可引用材料',
    grounded: '基于本地材料',
    notGrounded: '材料不足',
    model: '模型',
    tokens: 'Token',
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
    tools: 'Tool activity',
    sources: 'Sources',
    noSource: 'No citable local material was found',
    grounded: 'Grounded locally',
    notGrounded: 'Insufficient material',
    model: 'Model',
    tokens: 'Tokens',
    safety: 'This is research assistance. Verify important claims against the original papers.',
    examples: [
      'Summarize the main research gaps in my knowledge base',
      'Compare common methods in my Zotero literature',
      'Propose three testable questions from my current evidence',
    ],
  }, [isChinese])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-16)))
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    let active = true
    void zoteroApi.status()
      .then(() => active && setZoteroConnected(true))
      .catch(() => active && setZoteroConnected(false))
    return () => { active = false }
  }, [])

  const submit = async () => {
    const cleanQuestion = question.trim()
    if (!cleanQuestion || sending) return
    const history: AgentMessage[] = messages.slice(-6).map(({ role, content }) => ({ role, content }))
    const userEntry: ChatEntry = { id: newId(), role: 'user', content: cleanQuestion }
    setMessages((current) => [...current, userEntry])
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
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: 'assistant',
          content: response.data.answer,
          result: response.data,
        },
      ])
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail
        || (isChinese ? '智能体暂时无法回答，请检查模型和 Zotero 设置。' : 'The assistant could not answer. Check model and Zotero settings.')
      )
    } finally {
      setSending(false)
    }
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
          <div className="flex min-h-[480px] flex-col">
            <div className="custom-scrollbar flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-7">
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
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                  {message.result && <AgentTrace result={message.result} copy={copy} />}
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
                {messages.length > 0 && <button onClick={() => { setMessages([]); setError('') }} className="inline-flex shrink-0 items-center gap-1 hover:text-[var(--ui-text)]"><Eraser className="h-3.5 w-3.5" />{copy.clear}</button>}
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

function AgentTrace({ result, copy }: { result: AgentChatResponse; copy: Record<string, any> }) {
  return (
    <div className="mt-3 space-y-3 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-3 text-xs text-[var(--ui-text-soft)]">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-semibold ${result.grounded ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}`}>
          {result.grounded ? <ShieldCheck className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
          {result.grounded ? copy.grounded : copy.notGrounded}
        </span>
        {result.model && <span>{copy.model}: {result.provider}/{result.model}</span>}
        <span>{copy.tokens}: {result.total_tokens}</span>
      </div>
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
              return <div key={citation.id} className="rounded-lg border border-[var(--ui-border)] px-2.5 py-2">
                <div className="flex items-start gap-2">
                  <span className="font-mono font-bold text-[var(--ui-accent)]">[{citation.id}]</span>
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 font-medium text-[var(--ui-text)]">{citation.title}</p>
                    <p className="mt-1 uppercase tracking-wide text-[10px] text-[var(--ui-muted)]">{citation.source}</p>
                  </div>
                  {safeUrl && <a href={safeUrl} target="_blank" rel="noreferrer" aria-label={citation.title}><ExternalLink className="h-3.5 w-3.5" /></a>}
                </div>
              </div>
            })}
          </div>
        ) : <p>{copy.noSource}</p>}
      </div>
    </div>
  )
}
