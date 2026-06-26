import React, { useState } from 'react'
import { Copy, CheckCircle } from 'lucide-react'

const SQL_KEYWORDS = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|DROP|ALTER|TABLE|INDEX|VIEW|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|IN|NOT|IS|NULL|AND|OR|LIKE|BETWEEN|EXISTS|UNION|ALL|CASE|WHEN|THEN|ELSE|END|WITH|ASC|DESC|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|DEFAULT|CONSTRAINT)\b/gi

function highlightSql(sql) {
  if (!sql) return []
  const parts = []
  let last = 0
  let match

  const regex = new RegExp(SQL_KEYWORDS.source, 'gi')
  while ((match = regex.exec(sql)) !== null) {
    if (match.index > last) {
      parts.push({ text: sql.slice(last, match.index), type: 'plain' })
    }
    parts.push({ text: match[0], type: 'keyword' })
    last = match.index + match[0].length
  }
  if (last < sql.length) parts.push({ text: sql.slice(last), type: 'plain' })
  return parts
}

export default function SqlPanel({ sql, queryType }) {
  const [copied, setCopied] = useState(false)
  const parts = highlightSql(sql)

  const handleCopy = () => {
    navigator.clipboard.writeText(sql || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-700">
        <span className="text-xs font-mono text-slate-500">{queryType || 'SQL'}</span>
        <button onClick={handleCopy} className="btn-ghost py-0.5 px-2 text-xs flex items-center gap-1">
          {copied ? <CheckCircle size={12} className="text-emerald-400" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto bg-slate-900/50 leading-relaxed whitespace-pre-wrap">
        {parts.map((p, i) =>
          p.type === 'keyword'
            ? <span key={i} className="text-brand-400 font-bold">{p.text}</span>
            : <span key={i}>{p.text}</span>
        )}
      </pre>
    </div>
  )
}
