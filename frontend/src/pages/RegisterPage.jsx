import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Bot, Mail, Lock, User, Loader2, Eye, EyeOff } from 'lucide-react'
import { authAPI } from '../utils/api'
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', username: '', password: '', full_name: '' })
  const [showPw, setShowPw] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const regMut = useMutation({
    mutationFn: (data) => authAPI.register(data),
    onSuccess: (r) => {
      const { access_token, refresh_token, user } = r.data
      setAuth(user, access_token, refresh_token)
      toast.success('Account created!')
      navigate('/')
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Registration failed'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    regMut.mutate(form)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: "var(--bg-base)" }}>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <div className="flex items-center gap-2.5 mb-8">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Bot size={16} className="text-white" />
          </div>
          <p className="text-sm font-semibold text-white">AI Database Copilot</p>
        </div>

        <h2 className="text-2xl font-bold text-white mb-1">Create account</h2>
        <p className="text-sm text-slate-500 mb-8">Start querying your databases with AI</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 mb-1.5 block">Full name (optional)</label>
            <div className="relative">
              <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input value={form.full_name} onChange={e => set('full_name', e.target.value)}
                placeholder="Aditya Kumar" className="input-base w-full pl-9 text-sm" />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1.5 block">Username</label>
            <div className="relative">
              <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input required value={form.username} onChange={e => set('username', e.target.value)}
                placeholder="aditya123" className="input-base w-full pl-9 text-sm" />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1.5 block">Email</label>
            <div className="relative">
              <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input type="email" required value={form.email} onChange={e => set('email', e.target.value)}
                placeholder="you@example.com" className="input-base w-full pl-9 text-sm" />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1.5 block">Password (min 8 chars)</label>
            <div className="relative">
              <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input type={showPw ? 'text' : 'password'} required value={form.password}
                onChange={e => set('password', e.target.value)}
                placeholder="••••••••" className="input-base w-full pl-9 pr-9 text-sm" />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={regMut.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 text-sm mt-2">
            {regMut.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            {regMut.isPending ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-400 hover:text-brand-300 transition-colors">Sign in</Link>
        </p>
      </motion.div>
    </div>
  )
}
