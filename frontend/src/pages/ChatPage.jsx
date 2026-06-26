import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Loader2, Bot, AlertTriangle,
  CheckCircle, Copy, Play, Share2, ChevronRight,
  BookOpen, Code2, Sparkles, Shield, Mic, MicOff,
  Globe, Download, Pin, PinOff, Zap, Activity
} from 'lucide-react'
import toast from 'react-hot-toast'
import { v4 as uuidv4 } from 'uuid'
import { queryAPI, schemaAPI } from '../utils/api'
import { useAppStore, useAuthStore } from '../store'
import RightPanel from '../components/sql/RightPanel'
import clsx from 'clsx'
import { generateSuggestions } from '../utils/promptSuggestions'

const MODE_CONFIG = {
  simple:    { icon: Sparkles, label: 'Simple',    color: 'text-indigo-400',  desc: 'Plain language results' },
  learning:  { icon: BookOpen, label: 'Learning',  color: 'text-emerald-400', desc: 'Clause-by-clause explanations' },
  developer: { icon: Code2,    label: 'Developer', color: 'text-amber-400',   desc: 'Full technical details' },
}

const LANGUAGES = [
  { code: 'en', label: '🇺🇸 English' },
  { code: 'hi', label: '🇮🇳 Hindi' },
  { code: 'es', label: '🇪🇸 Spanish' },
  { code: 'fr', label: '🇫🇷 French' },
  { code: 'de', label: '🇩🇪 German' },
  { code: 'ja', label: '🇯🇵 Japanese' },
  { code: 'zh', label: '🇨🇳 Chinese' },
  { code: 'pt', label: '🇧🇷 Portuguese' },
  { code: 'ar', label: '🇸🇦 Arabic' },
]

function estimateComplexity(text) {
  const lower = text.toLowerCase()
  const complexKw = ['join','group','having','subquery','union','aggregate','window','partition','rank']
  const score = complexKw.filter(k => lower.includes(k)).length + (text.length > 80 ? 1 : 0)
  if (score >= 3) return { label: 'Complex', color: 'text-red-400',    icon: Activity }
  if (score >= 1) return { label: 'Medium',  color: 'text-amber-400',  icon: Zap }
  return             { label: 'Simple',  color: 'text-emerald-400', icon: Zap }
}

export default function ChatPage() {
  const [input, setInput]       = useState('')
  const [lang, setLang]         = useState('en')
  const [showLang, setShowLang] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const recognitionRef = useRef(null)
  const localSessionId = useRef(uuidv4())
  const bottomRef  = useRef(null)
  const textareaRef = useRef(null)

  const { user }                    = useAuthStore()
  const {
    activeConnection, sessions, activeSessionId, createSession,
    addMessage, setCurrentQueryResult, setCurrentExecResult,
    currentQueryResult, currentExecResult, isGenerating, setIsGenerating,
    pinnedQuery, setPinnedQuery,
  } = useAppStore()

  const { data: schema } = useQuery({
    queryKey: ['schema', activeConnection?.id],
    queryFn: () => schemaAPI.getSchema(activeConnection.id).then(r => r.data),
    enabled: !!activeConnection?.id,
  })

  const smartPrompts = useMemo(() => generateSuggestions(schema), [schema])

  useEffect(() => { if (!activeSessionId) createSession() }, [activeSessionId])

  const sessionId = activeSessionId || localSessionId.current
  const messages  = sessions[sessionId] || []
  const complexity = input.trim() ? estimateComplexity(input) : null
  const ComplexIcon = complexity?.icon

  /* ── keyboard shortcut: Ctrl+K focuses textarea ── */
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === 'k') { e.preventDefault(); textareaRef.current?.focus() }
      if (e.ctrlKey && e.key === 'Enter') {
        // Execute last query
        const lastResult = messages.slice().reverse().find(m => m.type === 'query_result')
        if (lastResult?.data?.id) executeMut.mutate({ query_id: lastResult.data.id, confirm: true })
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [messages])

  /* ── Voice input ── */
  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { toast.error('Voice input not supported in this browser'); return }
    const r = new SR()
    r.lang = lang === 'hi' ? 'hi-IN' : lang === 'es' ? 'es-ES' : 'en-US'
    r.continuous = false
    r.interimResults = false
    r.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(prev => prev ? prev + ' ' + transcript : transcript)
      toast.success('Voice captured!')
    }
    r.onerror = () => { toast.error('Voice recognition failed'); setIsRecording(false) }
    r.onend   = () => setIsRecording(false)
    r.start()
    recognitionRef.current = r
    setIsRecording(true)
  }

  const stopVoice = () => {
    recognitionRef.current?.stop()
    setIsRecording(false)
  }

  /* ── Generate query ── */
  const generateMut = useMutation({
    mutationFn: (data) => queryAPI.generate(data),
    onSuccess: (r) => {
      const result = r.data
      setCurrentQueryResult(result)
      addMessage(sessionId, { role: 'assistant', type: 'query_result', data: result, id: uuidv4() })
      setIsGenerating(false)
    },
    onError: (e) => {
      const msg = e.response?.data?.detail || 'Failed to generate query'
      addMessage(sessionId, { role: 'assistant', type: 'error', text: msg, id: uuidv4() })
      setIsGenerating(false)
      toast.error(msg)
    },
  })

  const executeMut = useMutation({
    mutationFn: (data) => queryAPI.execute(data),
    onSuccess: (r) => {
      setCurrentExecResult(r.data)
      toast.success(`Done — ${r.data.rows?.length ?? r.data.rows_affected} rows in ${r.data.execution_time_ms?.toFixed(0)}ms`)
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Execution failed'),
  })

  const handleSubmit = useCallback((e) => {
    e?.preventDefault()
    const q = input.trim()
    if (!q || isGenerating) return
    if (!activeConnection) { toast.error('Select a database connection first'); return }
    addMessage(sessionId, { role: 'user', text: q, id: uuidv4() })
    setInput('')
    setIsGenerating(true)
    generateMut.mutate({
      natural_language: q,
      connection_id: activeConnection.id,
      session_id: sessionId,
      mode: user?.preferred_mode || 'simple',
      language: lang,
    })
  }, [input, isGenerating, activeConnection, sessionId, user, lang])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
  }
  // Clear pin when connection changes
useEffect(() => {
  setPinnedQuery(null)
  setCurrentQueryResult(null)
  setCurrentExecResult(null)
}, [activeConnection?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isGenerating])

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0">

        {/* ── Header bar ── */}
        <div className="flex items-center justify-between px-5 py-3 border-b shrink-0"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            {activeConnection ? (
              <>
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{activeConnection.name}</span>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>•</span>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{activeConnection.db_type}</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 rounded-full bg-slate-600" />
                <span className="text-sm" style={{ color: 'var(--text-muted)' }}>No database connected</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Language selector */}
            <div className="relative">
              <button
                onClick={() => setShowLang(!showLang)}
                className="flex items-center gap-1.5 text-xs px-2 py-1.5 rounded-lg hover:bg-[var(--bg-elevated)] transition-colors border"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                <Globe size={12} />
                {LANGUAGES.find(l => l.code === lang)?.label.split(' ')[0] || '🇺🇸'}
                {lang !== 'en' && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
              </button>
              <AnimatePresence>
                {showLang && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="absolute right-0 top-full mt-1 z-50 rounded-xl shadow-xl overflow-hidden w-44"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                  >
                    {LANGUAGES.map(l => (
                      <button key={l.code} onClick={() => { setLang(l.code); setShowLang(false) }}
                        className={clsx(
                          'w-full text-left px-3 py-2 text-sm transition-colors hover:bg-[var(--bg-hover)]',
                          lang === l.code && 'text-indigo-400 font-medium'
                        )}
                        style={{ color: lang === l.code ? undefined : 'var(--text-secondary)' }}>
                        {l.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <ModeSelector />
          </div>
        </div>

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5"
          style={{ background: 'var(--bg-base)' }}>
          {isEmpty && (
            <EmptyState
              activeConnection={activeConnection}
              prompts={smartPrompts}
              onPrompt={(p) => { setInput(p); textareaRef.current?.focus() }}
            />
          )}

          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onExecute={(queryId, confirm) => executeMut.mutate({ query_id: queryId, confirm })}
              isExecuting={executeMut.isPending}
              onPin={(data) => setPinnedQuery(pinnedQuery?.id === data.id ? null : data)}
              isPinned={pinnedQuery?.id === msg?.data?.id}
            />
          ))}

          {isGenerating && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* ── Input area ── */}
        <div className="p-4 border-t shrink-0"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={activeConnection
                ? 'Ask anything about your data… (Enter to send)'
                : 'Select a database connection to start'}
              disabled={!activeConnection || isGenerating}
              rows={1}
              className="chat-input w-full resize-none pr-24 text-sm min-h-[50px] max-h-36 py-3.5 leading-relaxed"
              style={{ height: 'auto' }}
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = `${e.target.scrollHeight}px` }}
            />

            {/* Right action cluster */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              {/* Voice */}
              <button
                type="button"
                onClick={isRecording ? stopVoice : startVoice}
                disabled={!activeConnection}
                className={clsx(
                  'p-2 rounded-lg transition-all',
                  isRecording
                    ? 'bg-red-500/20 text-red-400 voice-pulse'
                    : 'hover:bg-[var(--bg-elevated)] disabled:opacity-30'
                )}
                style={{ color: isRecording ? undefined : 'var(--text-muted)' }}
                title={isRecording ? 'Stop recording' : 'Voice input'}
              >
                {isRecording ? <MicOff size={14} /> : <Mic size={14} />}
              </button>

              {/* Send */}
              <button
                type="submit"
                disabled={!input.trim() || !activeConnection || isGenerating}
                className="btn-primary px-3 py-1.5 text-sm"
              >
                {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              </button>
            </div>
          </form>

          {/* Bottom meta row */}
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-3">
              {/* Character count */}
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {input.length}/2000
              </span>
              {/* Complexity indicator */}
              {complexity && (
                <span className={clsx('text-xs flex items-center gap-1', complexity.color)}>
                  <ComplexIcon size={10} />
                  {complexity.label}
                </span>
              )}
              {/* Active language badge */}
              {lang !== 'en' && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/25">
                  {LANGUAGES.find(l => l.code === lang)?.label}
                </span>
              )}
            </div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              AI-generated SQL — review before executing on production.
            </p>
          </div>
        </div>
      </div>

      {/* ── Right panel ── */}
      {(currentQueryResult || pinnedQuery) && (
        <RightPanel
          queryResult={pinnedQuery || currentQueryResult}
          execResult={currentExecResult}
          onExecute={(queryId, confirm) => executeMut.mutate({ query_id: queryId, confirm })}
          isExecuting={executeMut.isPending}
          isPinned={!!pinnedQuery}
        />
      )}
    </div>
  )
}

/* ── Empty state ── */
function EmptyState({ onPrompt, activeConnection, prompts }) {
  const safePrompts = prompts?.length ? prompts : [
    'Show all tables and their row counts',
    'Find the top 10 records by date',
    'Show table relationships',
    'Count records grouped by category',
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-8">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 15 }}
        className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/20 flex items-center justify-center mb-5 glow-brand"
      >
        <Bot size={28} className="text-indigo-400" />
      </motion.div>
      <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>AI Database Copilot</h2>
      <p className="text-sm mb-6 max-w-md" style={{ color: 'var(--text-secondary)' }}>
        Ask questions in plain English — or any language. Get optimized SQL, explanations, and instant results.
      </p>

      {activeConnection && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="mb-5 rounded-xl px-4 py-3 max-w-md w-full"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Connected to {activeConnection.name}</p>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Suggestions below are generated from your database schema.
          </p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 gap-2 w-full max-w-md">
        {safePrompts.map((p, i) => (
          <motion.button
            key={p}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.05 * i }}
            type="button"
            onClick={() => onPrompt(p)}
            className="text-left text-sm px-4 py-3 rounded-xl border transition-all group hover:border-indigo-500/30"
            style={{
              background: 'var(--bg-surface)',
              borderColor: 'var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <span className="text-indigo-400 mr-2 group-hover:translate-x-0.5 inline-block transition-transform">→</span>
            {p}
          </motion.button>
        ))}
      </div>
    </div>
  )
}

/* ── Message bubble ── */
function MessageBubble({ message, onExecute, isExecuting, onPin, isPinned }) {
  if (message.role === 'user') {
    return (
      <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex justify-end">
        <div style={{
          maxWidth: '520px',
          background: 'linear-gradient(135deg, rgba(79,70,229,0.25), rgba(124,58,237,0.18))',
          border: '1px solid rgba(99,102,241,0.28)',
          borderRadius: '18px 4px 18px 18px',
          padding: '10px 16px',
          boxShadow: '0 4px 16px rgba(79,70,229,0.12)',
        }}>
          <p style={{ fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.6 }}>{message.text}</p>
        </div>
      </motion.div>
    )
  }

  if (message.type === 'error') {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
        <div className="w-7 h-7 rounded-lg bg-red-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <AlertTriangle size={14} className="text-red-400" />
        </div>
        <div className="rounded-xl px-4 py-3 text-sm text-red-300 bg-red-500/10 border border-red-500/25">
          {message.text}
        </div>
      </motion.div>
    )
  }

  if (message.type === 'query_result') {
    const { data } = message
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
        <div style={{
          width: '28px', height: '28px', borderRadius: '8px', flexShrink: 0, marginTop: '2px',
          background: 'linear-gradient(135deg, rgba(79,70,229,0.3), rgba(124,58,237,0.2))',
          border: '1px solid rgba(99,102,241,0.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 12px rgba(99,102,241,0.2)',
        }}>
          <Bot size={14} style={{ color: 'var(--accent-2)' }} />
        </div>

        <div className="flex-1 space-y-3 max-w-2xl">
          {/* Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <ConfidenceBadge score={data.confidence_score} />
            <RiskBadge level={data.risk_level} />
            <span className="text-xs font-mono-code" style={{ color: 'var(--text-muted)' }}>{data.query_type}</span>
          </div>

          {/* Explanation */}
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.explanation}</p>

          {/* SQL block */}
          <div style={{
            borderRadius: '12px', overflow: 'hidden',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-strong)',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px',
              borderBottom: '1px solid var(--border)',
              background: 'rgba(99,102,241,0.04)',
            }}>
              <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono',monospace", color: 'var(--accent-2)', fontWeight: 600 }}>{data.query_type}</span>
              <CopyButton text={data.generated_sql} />
            </div>
            <pre style={{
              padding: '14px', fontSize: '12px',
              fontFamily: "'JetBrains Mono',monospace",
              color: 'var(--text-secondary)',
              overflowX: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.7,
            }}>
              <SqlHighlight sql={data.generated_sql} />
            </pre>
          </div>

          {/* Warnings */}
          {data.warnings?.length > 0 && (
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/25 rounded-lg px-3 py-2">
              <AlertTriangle size={12} className="text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                {data.warnings.map((w, i) => <p key={i} className="text-xs text-amber-300">{w}</p>)}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => onExecute(data.id, data.risk_level === 'low' || data.risk_level === 'medium')}
              disabled={isExecuting || !data.id}
              className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5"
            >
              {isExecuting ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              Run Query
            </button>

            {/* Pin */}
            <button
              type="button"
              onClick={() => onPin(data)}
              className={clsx('text-xs px-3 py-1.5 flex items-center gap-1.5 rounded-lg border transition-all',
                isPinned
                  ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-400'
                  : 'btn-secondary'
              )}
              title="Pin to right panel"
            >
              {isPinned ? <PinOff size={12} /> : <Pin size={12} />}
              {isPinned ? 'Unpin' : 'Pin'}
            </button>

            {/* Share */}
            {data.share_token && (
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/share/${data.share_token}`)
                  toast.success('Share link copied!')
                }}
                className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5"
              >
                <Share2 size={12} /> Share
              </button>
            )}
          </div>
        </div>
      </motion.div>
    )
  }
  return null
}

function TypingIndicator() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
      <div className="w-7 h-7 rounded-lg bg-indigo-600/20 flex items-center justify-center shrink-0">
        <Bot size={14} className="text-indigo-400" />
      </div>
      <div className="rounded-xl px-4 py-3 flex items-center gap-1.5"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        {[0,1,2].map(i => (
          <div key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
            style={{ background: 'var(--text-muted)', animationDelay: `${i * 150}ms` }} />
        ))}
      </div>
    </motion.div>
  )
}

function ConfidenceBadge({ score }) {
  const pct = Math.round((score || 0) * 100)
  const color = pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-red-400'
  return (
    <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full border', color)}
      style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)' }}>
      {pct}% confidence
    </span>
  )
}

function RiskBadge({ level = 'low' }) {
  return (
    <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full capitalize', `risk-${level}`)}>
      <Shield size={9} className="inline mr-1" />{level} risk
    </span>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button type="button" onClick={() => { navigator.clipboard.writeText(text || ''); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="btn-ghost py-0.5 px-2 text-xs">
      {copied ? <CheckCircle size={12} className="text-emerald-400" /> : <Copy size={12} />}
    </button>
  )
}

function SqlHighlight({ sql }) {
  if (!sql) return null
  const KW = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|INTO|VALUES|SET|AND|OR|NOT|NULL|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|IN|LIKE|BETWEEN|IS|DESC|ASC|WITH|CASE|WHEN|THEN|ELSE|END)\b/gi
  const testKW = /^(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|INTO|VALUES|SET|AND|OR|NOT|NULL|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|IN|LIKE|BETWEEN|IS|DESC|ASC|WITH|CASE|WHEN|THEN|ELSE|END)$/i
  return sql.split(KW).map((p, i) =>
    testKW.test(p) ? <span key={i} className="text-indigo-400 font-semibold">{p}</span> : <span key={i}>{p}</span>
  )
}

function ModeSelector() {
  const { user, updateMode } = useAuthStore()
  const [open, setOpen] = useState(false)
  const current = MODE_CONFIG[user?.preferred_mode || 'simple']
  const Icon = current.icon
  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs px-2 py-1.5 rounded-lg border transition-colors hover:bg-[var(--bg-elevated)]"
        style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
        <Icon size={12} className={current.color} />
        {current.label}
        <ChevronRight size={10} className={clsx('transition-transform', open && 'rotate-90')} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="absolute right-0 top-full mt-1 z-50 rounded-xl shadow-xl overflow-hidden w-48"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            {Object.entries(MODE_CONFIG).map(([key, cfg]) => {
              const MIcon = cfg.icon
              return (
                <button key={key} type="button" onClick={() => { updateMode(key); setOpen(false) }}
                  className={clsx('w-full flex items-start gap-2 px-3 py-2.5 text-left transition-colors hover:bg-[var(--bg-hover)]',
                    user?.preferred_mode === key && 'bg-[var(--bg-hover)]')}>
                  <MIcon size={14} className={clsx(cfg.color, 'mt-0.5 shrink-0')} />
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{cfg.label}</p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{cfg.desc}</p>
                  </div>
                </button>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
