import React, { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { historyAPI } from '../utils/api'
import {
  History, Star, Trash2, Copy, Share2, Search,
  ChevronDown, Shield, CheckCircle, XCircle, Clock,
  Loader2, RotateCcw, Timer, Rows3, Database, Filter,
  TrendingUp, Zap
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { formatDistanceToNow, isToday, isYesterday, isThisWeek, format } from 'date-fns'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const QUERY_TYPES = ['', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']
const STATUSES    = ['', 'executed', 'generated', 'failed', 'blocked']

/* ── query type config ─────────────────────────────────────────────────── */
const QTYPE_CONFIG = {
  SELECT: { dot: 'bg-emerald-500',    label: 'SELECT', badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' },
  INSERT: { dot: 'bg-blue-500',       label: 'INSERT', badge: 'bg-blue-500/15 text-blue-400 border-blue-500/25' },
  UPDATE: { dot: 'bg-amber-500',      label: 'UPDATE', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/25' },
  DELETE: { dot: 'bg-red-500',        label: 'DELETE', badge: 'bg-red-500/15 text-red-400 border-red-500/25' },
  DEFAULT:{ dot: 'bg-slate-500',      label: 'SQL',    badge: 'bg-slate-500/15 text-slate-400 border-slate-500/25' },
}

const STATUS_CONFIG = {
  executed: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  generated:{ icon: Clock,       color: 'text-slate-400',   bg: 'bg-slate-500/10' },
  failed:   { icon: XCircle,     color: 'text-red-400',     bg: 'bg-red-500/10' },
  blocked:  { icon: Shield,      color: 'text-orange-400',  bg: 'bg-orange-500/10' },
}

function groupByDate(items) {
  const groups = {}
  items.forEach(item => {
    const d = new Date(item.created_at)
    let label
    if (isToday(d))         label = 'Today'
    else if (isYesterday(d)) label = 'Yesterday'
    else if (isThisWeek(d)) label = format(d, 'EEEE')   // Monday, Tuesday…
    else                    label = format(d, 'MMM d, yyyy')
    if (!groups[label]) groups[label] = []
    groups[label].push(item)
  })
  return groups
}

/* ══════════════════════════════════════════════════════════════════════════ */
export default function HistoryPage() {
  const [search, setSearch]       = useState('')
  const [queryType, setQueryType] = useState('')
  const [status, setStatus]       = useState('')
  const [favOnly, setFavOnly]     = useState(false)
  const [page, setPage]           = useState(1)
  const [showFilters, setShowFilters] = useState(false)
  const qc = useQueryClient()

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['history', { search, queryType, status, favOnly, page }],
    queryFn: () =>
      historyAPI.getHistory({
        search:        search || undefined,
        query_type:    queryType || undefined,
        status:        status || undefined,
        favorites_only: favOnly,
        page,
        limit: 30,
      }).then(r => r.data),
    keepPreviousData: true,
  })

  const favMut = useMutation({
    mutationFn: (id) => historyAPI.toggleFavorite(id),
    onSuccess: () => qc.invalidateQueries(['history']),
  })
  const delMut = useMutation({
    mutationFn: (id) => historyAPI.deleteEntry(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['history']) },
  })

  const grouped = groupByDate(items)
  const activeFilterCount = [queryType, status, favOnly].filter(Boolean).length

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: 'var(--bg-base)' }}>
      <div className="max-w-3xl mx-auto px-5 py-6 space-y-5">

        {/* ── Header ── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2.5" style={{ color: 'var(--text-primary)' }}>
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 flex items-center justify-center">
                <History size={16} className="text-indigo-400" />
              </div>
              Query History
            </h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {items.length} {items.length === 1 ? 'query' : 'queries'} found
            </p>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3">
            <MiniStat icon={CheckCircle} label="Executed" value={items.filter(i => i.status === 'executed').length} color="text-emerald-400" />
            <MiniStat icon={Star} label="Saved" value={items.filter(i => i.is_favorite).length} color="text-amber-400" />
          </div>
        </div>

        {/* ── Search + Filter bar ── */}
        <div className="space-y-2">
          <div className="flex gap-2">
            {/* Search */}
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1) }}
                placeholder="Search queries, SQL, keywords…"
                className="input-base w-full pl-9 text-sm"
              />
              {search && (
                <button onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs"
                  style={{ color: 'var(--text-muted)' }}>
                  ✕
                </button>
              )}
            </div>

            {/* Filter toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors',
                (showFilters || activeFilterCount > 0)
                  ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-400'
                  : 'btn-secondary'
              )}
            >
              <Filter size={13} />
              Filters
              {activeFilterCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>

            {/* Favorites shortcut */}
            <button
              onClick={() => { setFavOnly(!favOnly); setPage(1) }}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-all',
                favOnly
                  ? 'bg-amber-500/20 border-amber-500/40 text-amber-400'
                  : 'btn-secondary'
              )}
            >
              <Star size={13} className={favOnly ? 'fill-amber-400' : ''} />
              {favOnly ? 'Favorites' : '★'}
            </button>
          </div>

          {/* Expanded filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="flex gap-2 pt-1">
                  <select value={queryType} onChange={e => { setQueryType(e.target.value); setPage(1) }}
                    className="input-base text-sm flex-1">
                    {QUERY_TYPES.map(t => <option key={t} value={t}>{t || 'All query types'}</option>)}
                  </select>
                  <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}
                    className="input-base text-sm flex-1">
                    {STATUSES.map(s => <option key={s} value={s}>{s || 'All statuses'}</option>)}
                  </select>
                  {activeFilterCount > 0 && (
                    <button onClick={() => { setQueryType(''); setStatus(''); setFavOnly(false) }}
                      className="btn-ghost px-3 py-2 text-xs flex items-center gap-1.5">
                      <RotateCcw size={11} /> Reset
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Content ── */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 size={24} className="animate-spin text-indigo-400" />
          </div>
        ) : items.length === 0 ? (
          <EmptyHistory hasSearch={!!search || !!queryType || !!status || favOnly} />
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([dateLabel, groupItems]) => (
              <div key={dateLabel}>
                {/* Date group header */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>
                    {dateLabel}
                  </span>
                  <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {groupItems.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="space-y-2">
                  <AnimatePresence>
                    {groupItems.map((item, i) => (
                      <HistoryCard
                        key={item.id}
                        item={item}
                        index={i}
                        onFav={() => favMut.mutate(item.id)}
                        onDelete={() => delMut.mutate(item.id)}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Pagination ── */}
        {items.length > 0 && (
          <div className="flex items-center justify-between pt-4 pb-2">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Page {page}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="btn-secondary px-4 py-1.5 text-sm disabled:opacity-40">← Prev</button>
              <button onClick={() => setPage(p => p + 1)} disabled={items.length < 30}
                className="btn-secondary px-4 py-1.5 text-sm disabled:opacity-40">Next →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── History Card ───────────────────────────────────────────────────────── */
function HistoryCard({ item, index, onFav, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied]     = useState(false)

  const qtConf   = QTYPE_CONFIG[item.query_type] || QTYPE_CONFIG.DEFAULT
  const stConf   = STATUS_CONFIG[item.status]
  const StatusIcon = stConf?.icon || Clock

  const handleCopy = () => {
    navigator.clipboard.writeText(item.generated_sql || '')
    setCopied(true)
    toast.success('SQL copied!')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleShare = () => {
    navigator.clipboard.writeText(`${window.location.origin}/share/${item.share_token}`)
    toast.success('Share link copied!')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -10 }}
      transition={{ delay: index * 0.025, duration: 0.2 }}
      className={`history-card group type-${item.query_type || "DEFAULT"}`}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">

          {/* ── Left: type indicator column ── */}
          <div className="flex flex-col items-center gap-1.5 pt-0.5 shrink-0">
            {/* Animated dot */}
            <div className="relative">
              <div className={clsx('w-2.5 h-2.5 rounded-full', qtConf.dot)} />
              {item.status === 'executed' && (
                <div className={clsx('absolute inset-0 rounded-full animate-ping opacity-40', qtConf.dot)} />
              )}
            </div>
            {/* Vertical connector */}
            {expanded && <div className="w-px flex-1 min-h-[16px]" style={{ background: 'var(--border)' }} />}
          </div>

          {/* ── Center: main content ── */}
          <div className="flex-1 min-w-0">
            {/* Top row: type badge + status + time */}
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              {/* Query type badge */}
              <span className={clsx(
                'inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border font-mono-code',
                qtConf.badge
              )}>
                {item.query_type || 'SQL'}
              </span>

              {/* Status badge */}
              {stConf && (
                <span className={clsx(
                  'inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
                  stConf.bg, stConf.color
                )}>
                  <StatusIcon size={10} />
                  {item.status}
                </span>
              )}

              {/* Risk badge */}
              {item.risk_level && item.risk_level !== 'low' && (
                <span className={clsx('text-xs px-2 py-0.5 rounded-full capitalize border', `risk-${item.risk_level}`)}>
                  <Shield size={9} className="inline mr-0.5" />
                  {item.risk_level}
                </span>
              )}

              {/* Timestamp */}
              <span className="text-xs ml-auto shrink-0" style={{ color: 'var(--text-muted)' }}>
                {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
              </span>
            </div>

            {/* Natural language query */}
            <p className="text-sm font-medium leading-snug mb-2" style={{ color: 'var(--text-primary)' }}>
              {item.natural_language}
            </p>

            {/* Stats strip */}
            <div className="flex items-center gap-4 flex-wrap">
              {item.confidence_score != null && (
                <StatPill
                  icon={TrendingUp}
                  label={`${Math.round(item.confidence_score * 100)}%`}
                  sublabel="confidence"
                  color={item.confidence_score >= 0.8 ? 'text-emerald-400' : item.confidence_score >= 0.6 ? 'text-amber-400' : 'text-red-400'}
                />
              )}
              {item.execution_time_ms != null && (
                <StatPill icon={Timer} label={`${item.execution_time_ms.toFixed(0)}ms`} sublabel="exec time" color="text-blue-400" />
              )}
              {item.rows_returned != null && (
                <StatPill icon={Rows3} label={item.rows_returned.toLocaleString()} sublabel="rows" color="text-indigo-400" />
              )}
              {item.rows_affected != null && item.rows_returned == null && (
                <StatPill icon={Zap} label={item.rows_affected.toLocaleString()} sublabel="affected" color="text-amber-400" />
              )}
            </div>
          </div>

          {/* ── Right: actions ── */}
          <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            {/* Favorite */}
            <button onClick={onFav} className="btn-ghost p-1.5" title="Favorite">
              <Star size={13} className={item.is_favorite ? 'fill-amber-400 text-amber-400' : ''} />
            </button>

            {/* Copy SQL */}
            {item.generated_sql && (
              <button onClick={handleCopy} className="btn-ghost p-1.5" title="Copy SQL">
                {copied
                  ? <CheckCircle size={13} className="text-emerald-400" />
                  : <Copy size={13} />
                }
              </button>
            )}

            {/* Share */}
            {item.share_token && (
              <button onClick={handleShare} className="btn-ghost p-1.5" title="Copy share link">
                <Share2 size={13} />
              </button>
            )}

            {/* Expand */}
            {item.generated_sql && (
              <button onClick={() => setExpanded(!expanded)} className="btn-ghost p-1.5" title="Show SQL">
                <ChevronDown size={13} className={clsx('transition-transform duration-200', expanded && 'rotate-180')} />
              </button>
            )}

            {/* Delete */}
            <button onClick={onDelete} className="btn-ghost p-1.5 hover:text-red-400" title="Delete">
              <Trash2 size={13} />
            </button>
          </div>
        </div>

        {/* ── Expanded SQL ── */}
        <AnimatePresence>
          {expanded && item.generated_sql && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-3 ml-5 rounded-xl overflow-hidden border" style={{ borderColor: 'var(--border)' }}>
                <div className="flex items-center justify-between px-3 py-2 border-b" style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)' }}>
                  <span className="text-xs font-mono-code" style={{ color: 'var(--text-muted)' }}>
                    Generated SQL
                  </span>
                  <button onClick={handleCopy} className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                    {copied ? <CheckCircle size={11} className="text-emerald-400" /> : <Copy size={11} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre className="p-4 text-xs font-mono-code overflow-x-auto whitespace-pre-wrap leading-relaxed"
                  style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>
                  <SqlHighlight sql={item.generated_sql} />
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/* ── Helpers ────────────────────────────────────────────────────────────── */
function StatPill({ icon: Icon, label, sublabel, color }) {
  return (
    <span className="stat-chip">
      <Icon size={10} style={{ color }} />
      <span style={{ color, fontWeight: 600 }}>{label}</span>
      <span>{sublabel}</span>
    </span>
  )
}

function MiniStat({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
      <Icon size={12} className={color} />
      <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{value}</span>
      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
    </div>
  )
}

function EmptyHistory({ hasSearch }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <History size={24} style={{ color: 'var(--text-muted)' }} />
      </div>
      <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
        {hasSearch ? 'No queries match your filters' : 'No query history yet'}
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
        {hasSearch ? 'Try clearing your search or filters' : 'Start chatting to generate SQL queries'}
      </p>
    </div>
  )
}

function SqlHighlight({ sql }) {
  if (!sql) return null
  const KW = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|INTO|VALUES|SET|AND|OR|NOT|NULL|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|IN|LIKE|BETWEEN|IS|DESC|ASC|WITH|CASE|WHEN|THEN|ELSE|END)\b/gi
  const parts = sql.split(KW)
  const testKW = /^(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|INTO|VALUES|SET|AND|OR|NOT|NULL|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|IN|LIKE|BETWEEN|IS|DESC|ASC|WITH|CASE|WHEN|THEN|ELSE|END)$/i
  return parts.map((p, i) =>
    testKW.test(p)
      ? <span key={i} className="text-indigo-400 font-semibold">{p}</span>
      : <span key={i}>{p}</span>
  )
}
