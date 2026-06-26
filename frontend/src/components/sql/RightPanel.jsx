import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Code2, BookOpen, Zap, Table2, AlertTriangle, Play, Download,
  Loader2, Copy, CheckCircle, X, ChevronDown, ChevronUp,
  TrendingUp, Shield, Lightbulb, BarChart2
} from 'lucide-react'
import clsx from 'clsx'
import ResultsTable from './ResultsTable'

const TABS = [
  { id: 'sql',          label: 'SQL',          icon: Code2 },
  { id: 'explanation',  label: 'Explain',       icon: BookOpen },
  { id: 'optimization', label: 'Optimize',      icon: Zap },
  { id: 'impact',       label: 'Impact',        icon: AlertTriangle },
  { id: 'results',      label: 'Results',       icon: Table2 },
]

export default function RightPanel({ queryResult, execResult, onExecute, isExecuting }) {
  const [activeTab, setActiveTab] = useState('sql')

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 440, opacity: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }} className="flex flex-col border-l shrink-0 overflow-hidden"
    >
      {/* Tab bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '4px',
        padding: '10px 12px 8px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        overflowX: 'auto',
        flexShrink: 0,
      }}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              padding: '5px 10px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: activeTab === id ? 600 : 400,
              whiteSpace: 'nowrap',
              border: activeTab === id ? '1px solid rgba(99,102,241,0.3)' : '1px solid transparent',
              background: activeTab === id ? 'rgba(99,102,241,0.12)' : 'transparent',
              color: activeTab === id ? 'var(--accent-3)' : 'var(--text-muted)',
              cursor: 'pointer',
              transition: 'all 0.15s',
              boxShadow: activeTab === id ? '0 0 8px rgba(99,102,241,0.15)' : 'none',
            }}
          >
            <Icon size={11} />
            {label}
            {id === 'results' && execResult && (
              <span style={{
                marginLeft: '2px', padding: '1px 5px', borderRadius: '99px',
                fontSize: '10px', fontWeight: 700, fontFamily: "'JetBrains Mono',monospace",
                background: 'rgba(99,102,241,0.2)', color: 'var(--accent-3)',
              }}>
                {execResult.rows?.length ?? execResult.rows_affected}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="p-4 space-y-4"
          >
            {activeTab === 'sql'          && <SqlTab q={queryResult} onExecute={onExecute} isExecuting={isExecuting} />}
            {activeTab === 'explanation'  && <ExplanationTab q={queryResult} />}
            {activeTab === 'optimization' && <OptimizationTab q={queryResult} />}
            {activeTab === 'impact'       && <ImpactTab q={queryResult} onExecute={onExecute} isExecuting={isExecuting} />}
            {activeTab === 'results'      && <ResultsTab execResult={execResult} onExecute={() => { onExecute(queryResult.id, true); setActiveTab('results') }} isExecuting={isExecuting} hasResult={!!execResult} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/* ── SQL Tab ── */
function SqlTab({ q, onExecute, isExecuting }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(q.generated_sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Scores row */}
      <div className="grid grid-cols-2 gap-3">
        <ScoreCard label="Confidence" value={q.confidence_score} color="brand" />
        <ScoreCard label="Optimization" value={q.optimization_score} color="emerald" />
      </div>

      {/* SQL code block */}
      <div className="rounded-xl border border-slate-700 overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">{q.query_type || 'SQL'}</span>
            <span className={clsx('text-xs px-2 py-0.5 rounded-full capitalize', `risk-${q.risk_level}`)}>
              <Shield size={9} className="inline mr-1" />{q.risk_level}
            </span>
          </div>
          <button onClick={handleCopy} className="btn-ghost py-0.5 px-2 text-xs flex items-center gap-1">
            {copied ? <CheckCircle size={12} className="text-emerald-400" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto bg-slate-900/50 leading-relaxed whitespace-pre-wrap">
          {formatSql(q.generated_sql)}
        </pre>
      </div>

      {/* Alternatives */}
      {q.alternatives?.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1"><Lightbulb size={11} /> Alternatives</p>
          <div className="space-y-2">
            {q.alternatives.slice(0, 2).map((alt, i) => (
              <CollapsibleAlt key={i} alt={alt} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {q.warnings?.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 space-y-1">
          {q.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-300 flex items-start gap-1.5">
              <AlertTriangle size={11} className="shrink-0 mt-0.5" />{w}
            </p>
          ))}
        </div>
      )}

      {/* Execute */}
      <button
        onClick={() => onExecute(q.id, q.risk_level === 'low' || q.risk_level === 'medium')}
        disabled={isExecuting || !q.id}
        className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
      >
        {isExecuting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
        {isExecuting ? 'Running…' : 'Execute Query'}
      </button>
    </div>
  )
}

/* ── Explanation Tab ── */
function ExplanationTab({ q }) {
  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <p className="text-sm text-slate-300 leading-relaxed">{q.explanation}</p>
      </div>

      {/* Clause-by-clause */}
      {q.clauses_explained && Object.keys(q.clauses_explained).length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-2">Clause breakdown</p>
          <div className="space-y-2">
            {Object.entries(q.clauses_explained).map(([clause, desc]) => (
              <div key={clause} className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                <span className="text-xs font-mono font-bold text-brand-400">{clause}</span>
                <p className="text-xs text-slate-400 mt-1">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Learning tips */}
      {q.learning_tips?.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1"><BookOpen size={11} /> Learning tips</p>
          <div className="space-y-2">
            {q.learning_tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                <span className="text-emerald-400 text-xs font-bold shrink-0">{i + 1}</span>
                <p className="text-xs text-emerald-300">{tip}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Optimization Tab ── */
function OptimizationTab({ q }) {
  const score = Math.round((q.optimization_score || 0) * 100)
  return (
    <div className="space-y-4">
      {/* Score meter */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400">Optimization score</span>
          <span className="text-sm font-bold text-emerald-400">{score}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${score}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className={clsx('h-full rounded-full', score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500')}
          />
        </div>
      </div>

      {/* Estimated stats */}
      <div className="grid grid-cols-2 gap-3">
        {q.estimated_rows != null && (
          <StatCard label="Est. rows" value={q.estimated_rows.toLocaleString()} icon={BarChart2} />
        )}
        {q.estimated_time_ms != null && (
          <StatCard label="Est. time" value={`${q.estimated_time_ms}ms`} icon={TrendingUp} />
        )}
      </div>

      {/* Tips */}
      {q.optimization_tips?.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1"><Zap size={11} /> Suggestions</p>
          <div className="space-y-2">
            {q.optimization_tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2 bg-brand-500/10 border border-brand-500/20 rounded-lg p-3">
                <Zap size={11} className="text-brand-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-300">{tip}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!q.optimization_tips || q.optimization_tips.length === 0) && (
        <div className="text-center py-8 text-slate-600">
          <CheckCircle size={28} className="mx-auto mb-2 text-emerald-600" />
          <p className="text-sm">Query looks well-optimized!</p>
        </div>
      )}
    </div>
  )
}

/* ── Impact Tab ── */
function ImpactTab({ q, onExecute, isExecuting }) {
  const isDangerous = q.risk_level === 'high' || q.risk_level === 'critical'
  const isMutation = ['UPDATE', 'DELETE', 'INSERT'].includes(q.query_type)

  return (
    <div className="space-y-4">
      {/* Risk summary */}
      <div className={clsx(
        'rounded-xl border p-4 flex items-start gap-3',
        q.risk_level === 'critical' ? 'bg-red-500/10 border-red-500/30' :
        q.risk_level === 'high'     ? 'bg-orange-500/10 border-orange-500/30' :
        q.risk_level === 'medium'   ? 'bg-amber-500/10 border-amber-500/30' :
                                      'bg-emerald-500/10 border-emerald-500/30'
      )}>
        <Shield size={18} className={clsx(
          'shrink-0 mt-0.5',
          q.risk_level === 'critical' ? 'text-red-400' :
          q.risk_level === 'high'     ? 'text-orange-400' :
          q.risk_level === 'medium'   ? 'text-amber-400' : 'text-emerald-400'
        )} />
        <div>
          <p className="text-sm font-semibold text-white capitalize">{q.risk_level} Risk</p>
          <p className="text-xs text-slate-400 mt-0.5">Score: {Math.round((q.risk_score || 0) * 100)}%</p>
        </div>
      </div>

      {/* Risk reasons */}
      {q.risk_reasons?.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-2">Why this risk level</p>
          <div className="space-y-1.5">
            {q.risk_reasons.map((r, i) => (
              <p key={i} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-slate-600 shrink-0">•</span>{r}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Impact stats */}
      {isMutation && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <p className="text-xs text-slate-500 font-medium">Predicted impact</p>
          {q.estimated_rows != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Rows affected</span>
              <span className="text-sm font-bold text-white">{q.estimated_rows.toLocaleString()}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Operation type</span>
            <span className="text-xs font-mono text-amber-400">{q.query_type}</span>
          </div>
        </div>
      )}

      {/* Confirmation for dangerous queries */}
      {isDangerous && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 space-y-3">
          <div className="flex items-start gap-2">
            <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">
              This is a <strong>{q.risk_level}</strong> risk operation. 
              Confirm you want to execute this query. This action may be irreversible.
            </p>
          </div>
          <button
            onClick={() => onExecute(q.id, true)}
            disabled={isExecuting}
            className="w-full bg-red-600 hover:bg-red-500 text-white text-xs font-medium px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
          >
            {isExecuting ? <Loader2 size={12} className="animate-spin" /> : <AlertTriangle size={12} />}
            I understand — Execute anyway
          </button>
        </div>
      )}

      {!isDangerous && (
        <button
          onClick={() => onExecute(q.id, true)}
          disabled={isExecuting || !q.id}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
        >
          {isExecuting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Execute Query
        </button>
      )}
    </div>
  )
}

/* ── Results Tab ── */
function ResultsTab({ execResult, onExecute, isExecuting, hasResult }) {
  if (!hasResult) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Table2 size={32} className="text-slate-700 mb-3" />
        <p className="text-sm text-slate-500">No results yet</p>
        <p className="text-xs text-slate-600 mt-1">Execute the query to see results here</p>
        <button onClick={onExecute} disabled={isExecuting} className="btn-primary mt-4 text-sm flex items-center gap-2">
          {isExecuting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Run Query
        </button>
      </div>
    )
  }

  if (!execResult.success) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
        <p className="text-xs text-red-300 font-mono whitespace-pre-wrap">{execResult.error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span className="flex items-center gap-1"><CheckCircle size={11} className="text-emerald-400" /> Success</span>
        <span>{execResult.rows?.length ?? execResult.rows_affected} rows</span>
        <span>{execResult.execution_time_ms?.toFixed(1)}ms</span>
      </div>
      {/* Export CSV */}
      <div className="flex justify-end">
        <button
          onClick={() => {
            const rows = execResult.rows || []
            const cols = execResult.columns || []
            if (!rows.length) return
            const csv = [cols.join(','), ...rows.map(r => cols.map(c => JSON.stringify(r[c] ?? '')).join(','))].join('\n')
            const a = document.createElement('a')
            a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv)
            a.download = 'query_results.csv'
            a.click()
          }}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors hover:bg-[var(--bg-elevated)]"
          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
        >
          <Download size={12} /> Export CSV
        </button>
      </div>
      <ResultsTable rows={execResult.rows || []} columns={execResult.columns || []} />
    </div>
  )
}

/* ── Helpers ── */
function ScoreCard({ label, value, color }) {
  const pct = Math.round((value || 0) * 100)
  const colorMap = {
    brand: { bar: 'bg-brand-500', text: 'text-brand-400' },
    emerald: { bar: 'bg-emerald-500', text: 'text-emerald-400' },
  }
  const c = colorMap[color] || colorMap.brand
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500">{label}</span>
        <span className={clsx('text-sm font-bold', c.text)}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className={clsx('h-full rounded-full', c.bar)}
        />
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 flex items-center gap-2">
      <Icon size={14} className="text-slate-500 shrink-0" />
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-white">{value}</p>
      </div>
    </div>
  )
}

function CollapsibleAlt({ alt, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
        <span>Option {index + 1} — {alt.reason}</span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            className="overflow-hidden">
            <pre className="px-3 pb-3 text-xs font-mono text-slate-300 whitespace-pre-wrap border-t border-slate-800 pt-2">
              {alt.sql}
            </pre>
            <p className="px-3 pb-3 text-xs text-slate-500">{alt.explanation}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function formatSql(sql) {
  if (!sql) return ''
  // Basic keyword highlighting — wrap with spans
  return sql
}
