import React from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { queryAPI } from '../utils/api'
import { Bot, Loader2, AlertTriangle, Copy, CheckCircle } from 'lucide-react'
import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'

export default function SharedQueryPage() {
  const { token } = useParams()
  const [copied, setCopied] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['shared', token],
    queryFn: () => queryAPI.getShared(token).then(r => r.data),
  })

  const handleCopy = () => {
    navigator.clipboard.writeText(data?.generated_sql || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">AI Database Copilot</p>
            <p className="text-xs text-slate-500">Shared query</p>
          </div>
        </div>

        {isLoading && (
          <div className="flex justify-center py-16">
            <Loader2 size={24} className="animate-spin text-brand-400" />
          </div>
        )}

        {isError && (
          <div className="card p-8 text-center">
            <AlertTriangle size={32} className="text-red-400 mx-auto mb-3" />
            <p className="text-white font-medium">Query not found</p>
            <p className="text-slate-500 text-sm mt-1">This shared link may have expired or been removed.</p>
          </div>
        )}

        {data && (
          <div className="space-y-4">
            {/* NL question */}
            <div className="card p-5">
              <p className="text-xs text-slate-500 mb-2">Question</p>
              <p className="text-slate-200">{data.natural_language}</p>
            </div>

            {/* SQL */}
            <div className="card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">{data.query_type || 'SQL'}</span>
                  <span className="text-xs bg-brand-600/20 text-brand-400 px-2 py-0.5 rounded-full">
                    {Math.round((data.confidence_score || 0) * 100)}% confidence
                  </span>
                </div>
                <button onClick={handleCopy} className="btn-ghost text-xs px-2 py-1 flex items-center gap-1">
                  {copied ? <CheckCircle size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="p-4 text-sm font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {data.generated_sql}
              </pre>
            </div>

            {/* Explanation */}
            {data.explanation && (
              <div className="card p-5">
                <p className="text-xs text-slate-500 mb-2">Explanation</p>
                <p className="text-slate-300 text-sm leading-relaxed">{data.explanation}</p>
              </div>
            )}

            <p className="text-xs text-slate-600 text-center">
              Shared {data.created_at ? formatDistanceToNow(new Date(data.created_at), { addSuffix: true }) : ''} •
              <a href="/" className="text-brand-500 ml-1 hover:text-brand-400">Try AI Database Copilot</a>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
