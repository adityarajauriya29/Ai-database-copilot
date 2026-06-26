import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Bot, Mail, Lock, Loader2, Eye, EyeOff, Database, Cpu, ShieldCheck } from 'lucide-react'
import { authAPI } from '../utils/api'
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'

const TICKER_ITEMS = [
  'SELECT * FROM customers WHERE revenue > 1000000',
  'Analyzing 48 table relationships…',
  'Confidence: 97% · Risk: Low · Time: 12ms',
  'UPDATE employees SET salary = salary * 1.1',
  'Blocked: DELETE without WHERE clause',
  'Generated JOIN across 5 tables in 0.3s',
  'schema fingerprint cached — 23 tables detected',
  'NL → SQL · Explain · Optimize · Execute',
]

const FEATURES = [
  { icon: Database, label: 'Schema-aware',  sub: 'Reads your real tables' },
  { icon: Cpu,      label: 'Gemini AI',     sub: 'Multi-model routing' },
  { icon: ShieldCheck, label: 'SQL Firewall', sub: 'Blocks dangerous ops' },
]

function TerminalTicker() {
  const [index, setIndex] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false)
      setTimeout(() => {
        setIndex(i => (i + 1) % TICKER_ITEMS.length)
        setVisible(true)
      }, 300)
    }, 2800)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      background: 'rgba(0,0,0,0.4)',
      border: '1px solid rgba(99,102,241,0.2)',
      borderRadius: '10px',
      padding: '12px 16px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '12px',
      minHeight: '44px',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    }}>
      <span style={{ color: '#6366f1', userSelect: 'none' }}>›</span>
      <span style={{
        color: '#a5b4fc',
        opacity: visible ? 1 : 0,
        transition: 'opacity 0.3s',
        flex: 1,
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
      }}>
        {TICKER_ITEMS[index]}
      </span>
      <span style={{ color: '#6366f1', animation: 'glowPulse 1s ease-in-out infinite' }}>▋</span>
    </div>
  )
}

export default function LoginPage() {
  const [email, setEmail]     = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]   = useState(false)
  const { setAuth }           = useAuthStore()
  const navigate              = useNavigate()

  const loginMut = useMutation({
    mutationFn: (creds) => authAPI.login(creds),
    onSuccess: (r) => {
      const { access_token, refresh_token, user } = r.data
      setAuth(user, access_token, refresh_token)
      toast.success(`Welcome back, ${user.username}!`)
      navigate('/')
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Login failed'),
  })

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--bg-base)', position: 'relative', overflow: 'hidden' }}>

      {/* ── Left panel ── */}
      <div style={{
        width: '480px', flexShrink: 0, padding: '40px',
        display: 'none',
        flexDirection: 'column', justifyContent: 'space-between',
        background: 'linear-gradient(160deg, rgba(99,102,241,0.06) 0%, transparent 60%)',
        borderRight: '1px solid var(--border)',
        position: 'relative',
      }} className="lg-panel">

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '12px',
            background: 'var(--gradient-brand)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 24px rgba(99,102,241,0.4)',
          }}>
            <Bot size={20} color="#fff" />
          </div>
          <div>
            <p style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>AI Database Copilot</p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono',monospace" }}>v1.0 · Enterprise</p>
          </div>
        </div>

        {/* Hero */}
        <div style={{ marginBottom: '8px' }}>
          <div style={{ marginBottom: '28px' }}>
            <h1 style={{ fontSize: '32px', fontWeight: 700, lineHeight: 1.25, marginBottom: '16px', color: 'var(--text-primary)' }}>
              Talk to your<br />
              <span className="text-gradient">database in plain English</span>
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Generate optimized SQL, understand query impact, and interact safely — no SQL expertise needed.
            </p>
          </div>

          {/* Feature chips */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '28px' }}>
            {FEATURES.map(({ icon: Icon, label, sub }) => (
              <div key={label} style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                padding: '10px 14px', borderRadius: '10px',
                background: 'rgba(99,102,241,0.06)',
                border: '1px solid var(--border)',
              }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '8px', flexShrink: 0,
                  background: 'rgba(99,102,241,0.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon size={15} color="var(--accent-2)" />
                </div>
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>{label}</p>
                  <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{sub}</p>
                </div>
              </div>
            ))}
          </div>

          <TerminalTicker />
        </div>

        <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono',monospace" }}>
          FastAPI · React · Gemini 2.0 Flash
        </p>
      </div>

      {/* ── Right — form ── */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          style={{ width: '100%', maxWidth: '380px' }}
        >
          {/* Mobile logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '36px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              background: 'var(--gradient-brand)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 16px rgba(99,102,241,0.35)',
            }}>
              <Bot size={17} color="#fff" />
            </div>
            <div>
              <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>AI Database Copilot</p>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Enterprise SQL Assistant</p>
            </div>
          </div>

          <h2 style={{ fontSize: '26px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '6px' }}>Sign in</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '32px' }}>
            Welcome back — let's query some data
          </p>

          {/* Form */}
          <form onSubmit={(e) => { e.preventDefault(); loginMut.mutate({ email, password }) }} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px', fontWeight: 500 }}>Email</label>
              <div style={{ position: 'relative' }}>
                <Mail size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input-base"
                  style={{ width: '100%', paddingLeft: '36px', fontSize: '14px' }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px', fontWeight: 500 }}>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type={showPw ? 'text' : 'password'} required value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-base"
                  style={{ width: '100%', paddingLeft: '36px', paddingRight: '40px', fontSize: '14px' }}
                />
                <button type="button" onClick={() => setShowPw(!showPw)} style={{
                  position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                  color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                }}>
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loginMut.isPending} className="btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '4px' }}>
              {loginMut.isPending ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : null}
              {loginMut.isPending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-muted)', marginTop: '24px' }}>
            No account?{' '}
            <Link to="/register" style={{ color: 'var(--accent-2)', textDecoration: 'none', fontWeight: 500 }}>
              Create one free
            </Link>
          </p>
        </motion.div>
      </div>

      <style>{`
        @media (min-width: 1024px) { .lg-panel { display: flex !important; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes glowPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  )
}
