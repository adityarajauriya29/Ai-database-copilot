import React, { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

export default function ResultsTable({ rows, columns }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 50

  if (!rows || rows.length === 0) {
    return <p className="text-xs text-slate-500 text-center py-6">No rows returned</p>
  }

  const cols = columns.length > 0 ? columns : Object.keys(rows[0] || {})

  let sorted = [...rows]
  if (sortCol) {
    sorted.sort((a, b) => {
      const av = a[sortCol], bv = b[sortCol]
      if (av == null) return 1
      if (bv == null) return -1
      const cmp = av < bv ? -1 : av > bv ? 1 : 0
      return sortDir === 'asc' ? cmp : -cmp
    })
  }

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const visible = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleSort = (col) => {
    if (sortCol === col) setDir(sortDir === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('asc') }
  }

  const setDir = (d) => setSortDir(d)

  return (
    <div className="space-y-2">
      <div className="overflow-auto rounded-lg border border-slate-800 max-h-80">
        <table className="w-full text-xs text-left min-w-max">
          <thead className="sticky top-0 bg-slate-900 border-b border-slate-800">
            <tr>
              {cols.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2 font-medium text-slate-400 cursor-pointer hover:text-slate-200 whitespace-nowrap select-none"
                >
                  <span className="flex items-center gap-1">
                    {col}
                    {sortCol === col
                      ? sortDir === 'asc' ? <ChevronUp size={10} /> : <ChevronDown size={10} />
                      : <ChevronUp size={10} className="opacity-0 group-hover:opacity-30" />
                    }
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, ri) => (
              <tr key={ri} className={clsx('border-b border-slate-800/50', ri % 2 === 0 ? 'bg-slate-900/30' : 'bg-transparent')}>
                {cols.map((col) => {
                  const val = row[col]
                  return (
                    <td key={col} className="px-3 py-2 text-slate-300 whitespace-nowrap max-w-xs truncate font-mono">
                      {val === null || val === undefined
                        ? <span className="text-slate-600 italic">null</span>
                        : String(val)
                      }
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{rows.length} total rows</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-ghost px-2 py-1 text-xs disabled:opacity-30">←</button>
            <span>{page + 1} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page === totalPages - 1} className="btn-ghost px-2 py-1 text-xs disabled:opacity-30">→</button>
          </div>
        </div>
      )}
    </div>
  )
}
