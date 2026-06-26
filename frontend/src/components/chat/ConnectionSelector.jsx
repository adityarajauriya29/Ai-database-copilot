import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Database,
  Plus,
  ChevronDown,
  Check,
  Loader2,
  Trash2,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { schemaAPI } from '../../utils/api'
import { useAppStore } from '../../store'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import NewConnectionModal from './NewConnectionModal'

export default function ConnectionSelector() {
  const [open, setOpen] = useState(false)
  const [showModal, setShowModal] = useState(false)

  const { activeConnection, setActiveConnection } = useAppStore()
  const qc = useQueryClient()

  const { data: connections = [], isLoading } = useQuery({
    queryKey: ['connections'],
    queryFn: () => schemaAPI.getConnections().then((r) => r.data),
  })

  const demoMut = useMutation({
    mutationFn: (name) => schemaAPI.connectDemo(name),

    onSuccess: async (r, name) => {
      toast.success(`Connected to Demo: ${name}`)

      await qc.invalidateQueries({
        queryKey: ['connections'],
      })

      const refreshed = await schemaAPI.getConnections()

      const demoName = `Demo: ${name.charAt(0).toUpperCase()}${name.slice(1)}`

      const conn = refreshed.data.find((c) => c.name === demoName)

      if (conn) {
        setActiveConnection(conn)
      }

      setOpen(false)
    },

    onError: (err) => {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Demo connection failed')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => schemaAPI.deleteConnection(id),

    onSuccess: () => {
      toast.success('Connection removed')

      qc.invalidateQueries({
        queryKey: ['connections'],
      })

      if (activeConnection) {
        setActiveConnection(null)
      }
    },

    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to remove connection')
    },
  })

  const refreshMut = useMutation({
    mutationFn: (id) => schemaAPI.refreshSchema(id),

    onSuccess: () => {
      toast.success('Schema refreshed')

      qc.invalidateQueries({
        queryKey: ['connections'],
      })
    },

    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to refresh schema')
    },
  })

  const handleSelect = (conn) => {
    setActiveConnection(conn)
    setOpen(false)
  }

  return (
    <>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border',
            activeConnection
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
          )}
        >
          <Database size={14} className="shrink-0" />

          <span className="flex-1 text-left truncate">
            {activeConnection?.name || 'Select database'}
          </span>

          <ChevronDown
            size={12}
            className={clsx(
              'shrink-0 transition-transform',
              open && 'rotate-180'
            )}
          />
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="absolute top-full left-0 right-0 mt-1 z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden"
            >
              <div className="p-2 border-b border-slate-700">
                <p className="text-xs text-slate-500 px-2 mb-1.5 flex items-center gap-1">
                  <Zap size={10} />
                  Quick demo
                </p>

                {['ecommerce', 'university', 'hr'].map((name) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => demoMut.mutate(name)}
                    disabled={demoMut.isPending}
                    className="w-full text-left px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded capitalize transition-colors flex items-center justify-between"
                  >
                    <span>{name}</span>
                    {demoMut.isPending && (
                      <Loader2 size={11} className="animate-spin text-slate-500" />
                    )}
                  </button>
                ))}
              </div>

              <div className="p-2 max-h-48 overflow-y-auto">
                {isLoading ? (
                  <div className="flex justify-center py-3">
                    <Loader2 size={14} className="animate-spin text-slate-500" />
                  </div>
                ) : connections.length === 0 ? (
                  <p className="text-xs text-slate-500 px-2 py-2">
                    No connections yet
                  </p>
                ) : (
                  connections.map((conn) => (
                    <div key={conn.id} className="flex items-center group">
                      <button
                        type="button"
                        onClick={() => handleSelect(conn)}
                        className="flex-1 flex items-center gap-2 px-2 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors text-left"
                      >
                        {activeConnection?.id === conn.id && (
                          <Check
                            size={10}
                            className="text-emerald-400 shrink-0"
                          />
                        )}

                        <span className="truncate">{conn.name}</span>

                        <span className="text-slate-600 text-xs ml-auto">
                          {conn.db_type}
                        </span>
                      </button>

                      <button
                        type="button"
                        onClick={() => refreshMut.mutate(conn.id)}
                        className="p-1 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-300"
                      >
                        <RefreshCw size={10} />
                      </button>

                      <button
                        type="button"
                        onClick={() => deleteMut.mutate(conn.id)}
                        className="p-1 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400"
                      >
                        <Trash2 size={10} />
                      </button>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(true)
                    setOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-brand-400 hover:bg-slate-700 rounded transition-colors"
                >
                  <Plus size={12} />
                  New connection
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {showModal && <NewConnectionModal onClose={() => setShowModal(false)} />}
    </>
  )
}