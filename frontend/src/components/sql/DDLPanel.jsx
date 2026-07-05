import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database, Wand2, Play, CheckCircle, XCircle,
  Loader2, AlertTriangle, RefreshCw, Copy, ChevronDown, ChevronUp
} from 'lucide-react'
import { queryAPI, schemaAPI } from '../../utils/api'
import { useAuthStore } from '../../store'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const DDL_EXAMPLES = [
  'Create a products table with id, name, price, category, and stock columns',
  'Add a created_at timestamp column to the orders table',
  'Create an index on the email column of users table',
  'Create a tags table with many-to-many relation to products',
]

export default function DDLPanel({ connectionId, onSchemaRefresh }) {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const [mode, setMode]           = useState('nl')   // 'nl' | 'raw'
  const [nlInput, setNlInput]     = useState('')
  const [rawSql, setRawSql]       = useState('')
  const [generatedSql, setGeneratedSql] = useState('')
  const [result, setResult]       = useState(null)
  const [showExamples, setShowExamples] = useState(false)

  const generateMut = useMutation({
    mutationFn: (data) => queryAPI.generateDDL(data),
    onSuccess: (r) => {
      setGeneratedSql(r.data.sql)
      if (r.data.warnings?.length) {
        r.data.warnings.forEach(w => toast(w, { icon: '⚠️' }))
      }
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'DDL generation failed'),
  })

  const executeMut = useMutation({
    mutationFn: (data) => queryAPI.executeDDL(data),
    onSuccess: (r) => {
      setResult(r.data)
      if (r.data.success) {
        toast.success(`DDL executed in ${r.data.execution_time_ms?.toFixed(0)}ms`)
        if (onSchemaRefresh) onSchemaRefresh()
      } else {
        toast.error('DDL execution failed')
      }
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Execution failed'),
  })

  const handleGenerate = () => {
    if (!nlInput.trim()) { toast.error('Enter a description'); return }
    if (!connectionId)   { toast.error('Select a connection first'); return }
    generateMut.mutate({ natural_language: nlInput, connection_id: connectionId })
  }

  const handleExecute = () => {
    const sql = mode === 'raw' ? rawSql : generatedSql
    if (!sql.trim()) { toast.error('No SQL to execute'); return }
    if (!connectionId) { toast.error('Select a connection first'); return }
    executeMut.mutate({ sql, connection_id: connectionId })
  }

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied!')
  }

  if (!isAdmin) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '32px 16px', textAlign: 'center', gap: '12px',
      }}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '12px',
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <AlertTriangle size={22} style={{ color: '#ef4444' }} />
        </div>
        <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Admin Required</p>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', maxWidth: '220px' }}>
          DDL commands (CREATE, DROP, ALTER) require admin role. Contact your administrator.
        </p>
      </div>
    )
  }

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Mode toggle */}
      <div style={{
        display: 'flex', gap: '4px', padding: '4px',
        background: 'var(--bg-elevated)', borderRadius: '10px',
        border: '1px solid var(--border)',
      }}>
        {[
          { id: 'nl',  label: '✨ AI Generate' },
          { id: 'raw', label: '⌨️ Raw SQL' },
        ].map(({ id, label }) => (
          <button key={id} onClick={() => setMode(id)} style={{
            flex: 1, padding: '7px 12px', borderRadius: '8px', fontSize: '12px',
            fontWeight: 500, border: 'none', cursor: 'pointer', transition: 'all 0.15s',
            background: mode === id ? 'var(--gradient-brand)' : 'transparent',
            color: mode === id ? '#fff' : 'var(--text-muted)',
            boxShadow: mode === id ? '0 2px 8px rgba(99,102,241,0.3)' : 'none',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* NL mode */}
      {mode === 'nl' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Describe what you want to create
            </label>
            <textarea
              value={nlInput}
              onChange={e => setNlInput(e.target.value)}
              placeholder="e.g. Create a products table with id, name, price, and category"
              rows={3}
              className="input-base"
              style={{ width: '100%', resize: 'none', fontSize: '13px' }}
            />
          </div>

          {/* Examples */}
          <div>
            <button onClick={() => setShowExamples(!showExamples)}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                fontSize: '11px', color: 'var(--text-muted)',
                background: 'none', border: 'none', cursor: 'pointer', padding: 0,
              }}>
              {showExamples ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              Examples
            </button>
            <AnimatePresence>
              {showExamples && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden', marginTop: '6px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {DDL_EXAMPLES.map((ex) => (
                      <button key={ex} onClick={() => setNlInput(ex)} style={{
                        textAlign: 'left', fontSize: '11px', color: 'var(--text-secondary)',
                        padding: '6px 10px', borderRadius: '6px', cursor: 'pointer',
                        background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                        transition: 'border-color 0.15s',
                      }}
                        onMouseEnter={e => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
                        onMouseLeave={e => e.target.style.borderColor = 'var(--border)'}
                      >
                        → {ex}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <button onClick={handleGenerate} disabled={generateMut.isPending || !nlInput.trim()}
            className="btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '13px' }}>
            {generateMut.isPending ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Wand2 size={13} />}
            {generateMut.isPending ? 'Generating…' : 'Generate DDL'}
          </button>

          {/* Generated SQL preview */}
          {generatedSql && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              style={{
                borderRadius: '10px', overflow: 'hidden',
                background: 'var(--bg-input)', border: '1px solid var(--border-strong)',
              }}>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', borderBottom: '1px solid var(--border)',
                background: 'rgba(99,102,241,0.05)',
              }}>
                <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono',monospace", color: 'var(--accent-2)', fontWeight: 600 }}>
                  Generated DDL
                </span>
                <button onClick={() => handleCopy(generatedSql)} style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px',
                }}>
                  <Copy size={11} /> Copy
                </button>
              </div>
              <pre style={{
                padding: '12px', fontSize: '12px',
                fontFamily: "'JetBrains Mono',monospace",
                color: 'var(--text-secondary)',
                overflowX: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.6, margin: 0,
              }}>
                {generatedSql}
              </pre>
            </motion.div>
          )}
        </div>
      )}

      {/* Raw SQL mode */}
      {mode === 'raw' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Enter DDL statement
            </label>
            <textarea
              value={rawSql}
              onChange={e => setRawSql(e.target.value)}
              placeholder="CREATE TABLE products (&#10;  id INTEGER PRIMARY KEY,&#10;  name TEXT NOT NULL,&#10;  price REAL&#10;);"
              rows={7}
              className="input-base font-mono-code"
              style={{ width: '100%', resize: 'vertical', fontSize: '12px', lineHeight: 1.6 }}
            />
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Allowed: CREATE · DROP · ALTER · TRUNCATE · RENAME
          </p>
        </div>
      )}

      {/* Execute button */}
      {(generatedSql || (mode === 'raw' && rawSql)) && (
        <button
          onClick={handleExecute}
          disabled={executeMut.isPending}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            padding: '10px', borderRadius: '10px', fontSize: '13px', fontWeight: 500,
            cursor: 'pointer', border: 'none', transition: 'all 0.15s',
            background: 'linear-gradient(135deg, #059669, #047857)',
            color: '#fff',
            boxShadow: '0 2px 8px rgba(5,150,105,0.3)',
            opacity: executeMut.isPending ? 0.6 : 1,
          }}
        >
          {executeMut.isPending
            ? <><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Executing…</>
            : <><Play size={13} /> Execute DDL</>
          }
        </button>
      )}

      {/* Result */}
      {result && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '12px 14px', borderRadius: '10px',
            background: result.success ? 'rgba(5,150,105,0.08)' : 'rgba(239,68,68,0.08)',
            border: `1px solid ${result.success ? 'rgba(5,150,105,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            {result.success
              ? <CheckCircle size={15} style={{ color: '#10b981' }} />
              : <XCircle size={15} style={{ color: '#ef4444' }} />
            }
            <span style={{ fontSize: '13px', fontWeight: 600, color: result.success ? '#10b981' : '#ef4444' }}>
              {result.success ? 'Success' : 'Failed'}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
            {result.message}
          </p>
          {result.success && (
            <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
              <span>{result.execution_time_ms?.toFixed(0)}ms</span>
              {result.schema_refreshed && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#10b981' }}>
                  <RefreshCw size={10} /> Schema refreshed
                </span>
              )}
            </div>
          )}
        </motion.div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
