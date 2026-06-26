import React, { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Database,
  RefreshCcw,
  Search,
  Table2,
  KeyRound,
  Link2,
  Columns3,
  Eye,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { schemaAPI } from '../utils/api'
import { useAppStore } from '../store'
import clsx from 'clsx'

export default function SchemaExplorerPage() {
  const [search, setSearch] = useState('')
  const [selectedTable, setSelectedTable] = useState(null)
  const [previewRows, setPreviewRows] = useState([])
  const [previewColumns, setPreviewColumns] = useState([])
  const [previewTableName, setPreviewTableName] = useState('')
  const [previewLimit, setPreviewLimit] = useState(100)

  const { activeConnection } = useAppStore()
  const queryClient = useQueryClient()

  const schemaQuery = useQuery({
    queryKey: ['schema', activeConnection?.id],
    queryFn: () => schemaAPI.getSchema(activeConnection.id),
    enabled: !!activeConnection?.id,
  })

  const refreshMutation = useMutation({
    mutationFn: () => schemaAPI.refreshSchema(activeConnection.id),
    onSuccess: () => {
      toast.success('Schema refreshed')
      queryClient.invalidateQueries({ queryKey: ['schema', activeConnection?.id] })
      setPreviewRows([])
      setPreviewColumns([])
      setPreviewTableName('')
    },
    onError: (e) => {
      toast.error(e.response?.data?.detail || 'Failed to refresh schema')
    },
  })

  const previewMutation = useMutation({
    mutationFn: () =>
      schemaAPI.previewTable(activeConnection.id, selectedTable.name, previewLimit),
    onSuccess: (res) => {
      setPreviewRows(res.data.rows || [])
      setPreviewColumns(res.data.columns || [])
      setPreviewTableName(res.data.table || selectedTable?.name || '')
      toast.success(`Loaded ${res.data.row_count || 0} rows`)
    },
    onError: (e) => {
      toast.error(e.response?.data?.detail || 'Failed to preview data')
    },
  })

  const schema = schemaQuery.data?.data || {}
  const tables = schema.tables || []

  const filteredTables = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return tables

    return tables.filter((table) => {
      const tableMatch = table.name?.toLowerCase().includes(q)
      const columnMatch = table.columns?.some((col) =>
        col.name?.toLowerCase().includes(q)
      )
      return tableMatch || columnMatch
    })
  }, [tables, search])

  useEffect(() => {
    if (filteredTables.length > 0) {
      const stillExists = filteredTables.some(
        (table) => table.name === selectedTable?.name
      )

      if (!selectedTable || !stillExists) {
        setSelectedTable(filteredTables[0])
        setPreviewRows([])
        setPreviewColumns([])
        setPreviewTableName('')
      }
    } else {
      setSelectedTable(null)
    }
  }, [filteredTables, selectedTable])

  const handleSelectTable = (table) => {
    setSelectedTable(table)
    setPreviewRows([])
    setPreviewColumns([])
    setPreviewTableName('')
  }

  if (!activeConnection) {
    return (
      <div className="h-full flex items-center justify-center text-center px-6">
        <div>
          <Database size={42} className="mx-auto text-slate-600 mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">
            No database selected
          </h2>
          <p className="text-sm text-slate-400">
            Select or connect a demo database from the sidebar to view its schema.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white flex items-center gap-2">
            <Database size={18} className="text-brand-400" />
            Schema Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Viewing schema for {activeConnection.name}
          </p>
        </div>

        <button
          type="button"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="btn-primary text-xs px-3 py-2 flex items-center gap-2"
        >
          <RefreshCcw
            size={14}
            className={refreshMutation.isPending ? 'animate-spin' : ''}
          />
          Refresh Schema
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] min-h-0 flex-1">
        <aside className="border-r border-slate-800 p-4 overflow-y-auto">
          <div className="relative mb-4">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tables or columns..."
              className="input-base w-full pl-9 text-sm"
            />
          </div>

          <div className="space-y-2">
            {filteredTables.map((table) => (
              <button
                key={table.name}
                type="button"
                onClick={() => handleSelectTable(table)}
                className={clsx(
                  'w-full text-left rounded-xl border px-3 py-3 transition-all',
                  selectedTable?.name === table.name
                    ? 'bg-brand-600/20 border-brand-600/40'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                )}
              >
                <div className="flex items-center gap-2">
                  <Table2 size={15} className="text-brand-400" />
                  <span className="text-sm font-medium text-slate-200 truncate">
                    {table.name}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {table.columns?.length || 0} columns
                </p>
              </button>
            ))}
          </div>
        </aside>

        <main className="p-6 overflow-y-auto">
          {schemaQuery.isLoading ? (
            <p className="text-sm text-slate-400">Loading schema...</p>
          ) : selectedTable ? (
            <div>
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Table2 size={20} className="text-brand-400" />
                    {selectedTable.name}
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Table columns, data types, primary keys, and foreign keys.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-xs text-slate-500 flex items-center gap-2">
                    <Columns3 size={14} />
                    {selectedTable.columns?.length || 0} columns
                  </div>

                  <select
                    value={previewLimit}
                    onChange={(e) => setPreviewLimit(Number(e.target.value))}
                    className="input-base text-xs px-2 py-2"
                  >
                    <option value={10}>10 rows</option>
                    <option value={50}>50 rows</option>
                    <option value={100}>100 rows</option>
                    <option value={-1}>All rows</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => previewMutation.mutate()}
                    disabled={previewMutation.isPending}
                    className="btn-primary text-xs px-3 py-2 flex items-center gap-2"
                  >
                    {previewMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Eye size={14} />
                    )}
                    Preview Data
                  </button>
                </div>
              </div>

              <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
                <table className="w-full text-sm">
                  <thead className="bg-slate-950/60 border-b border-slate-800">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400">
                        Column
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400">
                        Type
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400">
                        Keys
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {selectedTable.columns?.map((col) => (
                      <tr
                        key={col.name}
                        className="border-b border-slate-800/70 last:border-0"
                      >
                        <td className="px-4 py-3 text-slate-200 font-mono text-xs">
                          {col.name}
                        </td>
                        <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                          {col.type}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            {col.primary_key && (
                              <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                <KeyRound size={11} />
                                PK
                              </span>
                            )}

                            {col.foreign_key && (
                              <span className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/30 flex items-center gap-1">
                                <Link2 size={11} />
                                FK
                              </span>
                            )}

                            {!col.primary_key && !col.foreign_key && (
                              <span className="text-xs text-slate-600">—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {previewRows.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Eye size={15} className="text-brand-400" />
                      Preview Data: {previewTableName}
                    </h3>
                    <span className="text-xs text-slate-500">
                      Showing {previewRows.length} rows
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-950/60 border-b border-slate-800">
                        <tr>
                          {previewColumns.map((col) => (
                            <th
                              key={col}
                              className="text-left px-4 py-3 text-xs font-medium text-slate-400 whitespace-nowrap"
                            >
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>

                      <tbody>
                        {previewRows.map((row, rowIndex) => (
                          <tr
                            key={rowIndex}
                            className="border-b border-slate-800/70 last:border-0"
                          >
                            {previewColumns.map((col) => (
                              <td
                                key={col}
                                className="px-4 py-3 text-xs text-slate-300 whitespace-nowrap"
                              >
                                {row[col] === null || row[col] === undefined
                                  ? 'NULL'
                                  : String(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {previewMutation.isSuccess && previewRows.length === 0 && (
                <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-sm text-slate-400">
                    No rows found in this table.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              No schema available. Click Refresh Schema.
            </p>
          )}
        </main>
      </div>
    </div>
  )
}