import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Database, Loader2, Upload } from 'lucide-react'
import { schemaAPI } from '../../utils/api'
import { useAppStore } from '../../store'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'

const DB_TYPES = [
  { value: 'upload_sqlite', label: 'Upload SQLite File', defaultPort: null },
  { value: 'sqlite', label: 'SQLite (file path)', defaultPort: null },
  { value: 'postgresql', label: 'PostgreSQL', defaultPort: 5432 },
  { value: 'mysql', label: 'MySQL', defaultPort: 3306 },
]

export default function NewConnectionModal({ onClose }) {
  const [form, setForm] = useState({
    name: '',
    db_type: 'upload_sqlite',
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: '',
    is_readonly: true,
  })

  const [sqliteFile, setSqliteFile] = useState(null)

  const qc = useQueryClient()
  const { setActiveConnection } = useAppStore()

  const createMut = useMutation({
    mutationFn: (data) => schemaAPI.createConnection(data),
    onSuccess: (r) => {
      toast.success('Connection created!')
      qc.invalidateQueries({ queryKey: ['connections'] })
      setActiveConnection(r.data)
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Connection failed'),
  })

  const uploadMut = useMutation({
    mutationFn: (data) => schemaAPI.uploadSQLite(data),
    onSuccess: async (r) => {
      toast.success('SQLite database uploaded!')

      await qc.invalidateQueries({ queryKey: ['connections'] })

      const refreshed = await schemaAPI.getConnections()
      const conn = refreshed.data.find((c) => c.id === r.data.id)

      if (conn) {
        setActiveConnection(conn)
      }

      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Upload failed'),
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = (e) => {
    e.preventDefault()

    if (form.db_type === 'upload_sqlite') {
      if (!sqliteFile) {
        toast.error('Please select a SQLite database file')
        return
      }

      const formData = new FormData()
      formData.append('name', form.name)
      formData.append('is_readonly', form.is_readonly)
      formData.append('file', sqliteFile)

      uploadMut.mutate(formData)
      return
    }

    createMut.mutate(form)
  }

  const isPending = createMut.isPending || uploadMut.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl"
      >
        <div className="flex items-center gap-3 p-5 border-b border-slate-800">
          <Database size={18} className="text-brand-400" />
          <h2 className="text-base font-semibold text-white">New Connection</h2>
          <button type="button" onClick={onClose} className="ml-auto btn-ghost p-1.5">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Connection name</label>
            <input
              required
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="My Database"
              className="input-base w-full text-sm"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Database type</label>
            <select
              value={form.db_type}
              onChange={(e) => {
                const t = DB_TYPES.find((d) => d.value === e.target.value)
                setForm((f) => ({
                  ...f,
                  db_type: e.target.value,
                  port: t?.defaultPort || f.port,
                }))
              }}
              className="input-base w-full text-sm"
            >
              {DB_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          {form.db_type === 'upload_sqlite' ? (
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Choose SQLite file
              </label>
              <input
                required
                type="file"
                accept=".db,.sqlite,.sqlite3"
                onChange={(e) => setSqliteFile(e.target.files?.[0] || null)}
                className="input-base w-full text-sm"
              />
              <p className="text-xs text-slate-500 mt-1">
                Supported: .db, .sqlite, .sqlite3
              </p>
            </div>
          ) : form.db_type !== 'sqlite' ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-slate-400 mb-1 block">Host</label>
                  <input
                    value={form.host}
                    onChange={(e) => set('host', e.target.value)}
                    className="input-base w-full text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Port</label>
                  <input
                    type="number"
                    value={form.port}
                    onChange={(e) => set('port', +e.target.value)}
                    className="input-base w-full text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Database name</label>
                <input
                  required
                  value={form.database}
                  onChange={(e) => set('database', e.target.value)}
                  className="input-base w-full text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Username</label>
                  <input
                    value={form.username}
                    onChange={(e) => set('username', e.target.value)}
                    className="input-base w-full text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Password</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => set('password', e.target.value)}
                    className="input-base w-full text-sm"
                  />
                </div>
              </div>
            </>
          ) : (
            <div>
              <label className="text-xs text-slate-400 mb-1 block">File path</label>
              <input
                required
                value={form.database}
                onChange={(e) => set('database', e.target.value)}
                placeholder="./my_database.db"
                className="input-base w-full text-sm"
              />
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_readonly}
              onChange={(e) => set('is_readonly', e.target.checked)}
              className="rounded"
            />
            Read-only mode (safer)
          </label>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 text-sm">
              Cancel
            </button>

            <button
              type="submit"
              disabled={isPending}
              className="btn-primary flex-1 text-sm flex items-center justify-center gap-2"
            >
              {isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : form.db_type === 'upload_sqlite' ? (
                <Upload size={14} />
              ) : (
                <Database size={14} />
              )}
              {isPending ? 'Connecting…' : 'Connect'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}