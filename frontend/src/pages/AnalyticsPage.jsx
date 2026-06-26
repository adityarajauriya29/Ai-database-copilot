import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid
} from 'recharts'
import { analyticsAPI } from '../utils/api'
import { BarChart3, TrendingUp, CheckCircle, XCircle, Shield, Loader2, Clock } from 'lucide-react'
import { motion } from 'framer-motion'

const COLORS = ['#3366ff', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
const RISK_COLORS = { low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' }

const PERIODS = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
]

export default function AnalyticsPage() {
  const [period, setPeriod] = useState(30)

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', period],
    queryFn: () => analyticsAPI.getDashboard(period).then(r => r.data),
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-brand-400" />
      </div>
    )
  }

  const s = data?.summary || {}

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 size={22} className="text-brand-400" />
            Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">Query performance & usage insights</p>
        </div>
        <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
          {PERIODS.map(p => (
            <button key={p.days} onClick={() => setPeriod(p.days)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${period === p.days ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard icon={BarChart3} label="Total Queries" value={s.total_queries ?? 0} color="brand" />
        <SummaryCard icon={CheckCircle} label="Executed" value={s.executed ?? 0} color="emerald" />
        <SummaryCard icon={XCircle} label="Failed" value={s.failed ?? 0} color="red" />
        <SummaryCard icon={Clock} label="Avg Time" value={`${s.avg_execution_time_ms ?? 0}ms`} color="amber" />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Daily queries line chart */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={15} className="text-brand-400" />
            Queries over time
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data?.daily_queries || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="count" stroke="#3366ff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Query type bar chart */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Query Types</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data?.query_types || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="type" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(data?.query_types || []).map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk distribution pie */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Shield size={15} className="text-brand-400" />
            Risk Distribution
          </h3>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={data?.risk_distribution || []} dataKey="count" nameKey="level"
                  cx="50%" cy="50%" outerRadius={70} innerRadius={45}>
                  {(data?.risk_distribution || []).map((entry, i) => (
                    <Cell key={i} fill={RISK_COLORS[entry.level] || COLORS[i]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2">
              {(data?.risk_distribution || []).map((entry) => (
                <div key={entry.level} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: RISK_COLORS[entry.level] }} />
                    <span className="text-slate-400 capitalize">{entry.level}</span>
                  </span>
                  <span className="text-slate-300 font-medium">{entry.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top tables */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Most Queried Tables</h3>
          <div className="space-y-2">
            {(data?.top_tables || []).length === 0 ? (
              <p className="text-xs text-slate-600 text-center py-8">No table data yet</p>
            ) : (
              (data?.top_tables || []).map((t, i) => {
                const max = data.top_tables[0]?.count || 1
                const pct = (t.count / max) * 100
                return (
                  <div key={t.table} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-4">{i + 1}</span>
                    <span className="text-xs text-slate-300 font-mono w-24 truncate">{t.table}</span>
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, delay: i * 0.1 }}
                        className="h-full bg-brand-500 rounded-full"
                      />
                    </div>
                    <span className="text-xs text-slate-500 w-6 text-right">{t.count}</span>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function SummaryCard({ icon: Icon, label, value, color }) {
  const colors = {
    brand: 'text-brand-400 bg-brand-500/10 border-brand-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    red: 'text-red-400 bg-red-500/10 border-red-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-4"
    >
      <div className={`inline-flex items-center justify-center w-9 h-9 rounded-lg border mb-3 ${colors[color]}`}>
        <Icon size={16} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </motion.div>
  )
}
