import React, { useEffect, useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare, BarChart3, History, Database,
  LogOut, Plus, ChevronLeft, ChevronRight,
  Zap, Bot, Sun, Moon, Keyboard, X
} from 'lucide-react'
import { useAuthStore, useAppStore, useThemeStore } from '../../store'
import ConnectionSelector from '../chat/ConnectionSelector'

const navItems = [
  { to: '/',         icon: MessageSquare, label: 'Chat',      end: true },
  { to: '/schema',   icon: Database,      label: 'Schema'    },
  { to: '/analytics',icon: BarChart3,     label: 'Analytics' },
  { to: '/history',  icon: History,       label: 'History'   },
]

const SHORTCUTS = [
  { keys: ['Ctrl','K'],      desc: 'Focus chat input' },
  { keys: ['Enter'],         desc: 'Send message' },
  { keys: ['Shift','Enter'], desc: 'New line' },
  { keys: ['Ctrl','Enter'],  desc: 'Execute last query' },
  { keys: ['Ctrl','/'],      desc: 'New chat session' },
  { keys: ['?'],             desc: 'Toggle shortcuts' },
]

export default function Layout() {
  const { user, logout }                               = useAuthStore()
  const { sidebarOpen, setSidebarOpen, createSession } = useAppStore()
  const { theme, toggleTheme }                         = useThemeStore()
  const [showShortcuts, setShowShortcuts]              = useState(false)
  const navigate = useNavigate()

  const handleNewChat = () => { createSession(); navigate('/') }

  useEffect(() => {
    const handler = (e) => {
      if (e.key === '?' && !['INPUT','TEXTAREA'].includes(e.target.tagName)) setShowShortcuts(s => !s)
      if (e.key === 'Escape') setShowShortcuts(false)
      if (e.ctrlKey && e.key === '/') { e.preventDefault(); handleNewChat() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const initials = user?.username?.[0]?.toUpperCase() || '?'

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>

      {/* ══ SIDEBAR ══════════════════════════════════════════════════════════ */}
      <AnimatePresence initial={false}>
        {sidebarOpen ? (
          <motion.aside
            key="open"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            style={{
              display: 'flex', flexDirection: 'column', flexShrink: 0,
              overflow: 'hidden',
              background: 'var(--bg-surface)',
              borderRight: '1px solid var(--border)',
              position: 'relative',
            }}
          >
            {/* Top accent line */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: 'var(--gradient-brand)',
            }} />

            {/* Logo area */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '20px 16px 16px',
              borderBottom: '1px solid var(--border)',
            }}>
              <div style={{
                width: '32px', height: '32px', borderRadius: '9px', flexShrink: 0,
                background: 'var(--gradient-brand)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 0 16px rgba(99,102,241,0.35)',
              }}>
                <Bot size={15} color="#fff" />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                  DB Copilot
                </p>
                <p style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono',monospace" }}>
                  AI · SQL · Enterprise
                </p>
              </div>
              <div style={{ display: 'flex', gap: '2px' }}>
                <button onClick={toggleTheme} className="btn-ghost" style={{ padding: '6px' }}
                  title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
                  {theme === 'dark'
                    ? <Sun size={13} style={{ color: '#fbbf24' }} />
                    : <Moon size={13} style={{ color: 'var(--accent-2)' }} />
                  }
                </button>
                <button onClick={() => setSidebarOpen(false)} className="btn-ghost" style={{ padding: '6px' }}>
                  <ChevronLeft size={13} />
                </button>
              </div>
            </div>

            {/* New chat button */}
            <div style={{ padding: '12px 12px 8px' }}>
              <button onClick={handleNewChat} className="btn-primary"
                style={{ width: '100%', padding: '9px 14px', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px', borderRadius: '10px' }}>
                <Plus size={14} />
                New Chat
                <span style={{ marginLeft: 'auto', fontSize: '10px', opacity: 0.5, fontFamily: "'JetBrains Mono',monospace" }}>⌃/</span>
              </button>
            </div>

            {/* Connection selector */}
            <div style={{ padding: '0 12px 8px' }}>
              <ConnectionSelector />
            </div>

            {/* Nav */}
            <nav style={{ flex: 1, padding: '4px 12px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {navItems.map(({ to, icon: Icon, label, end }) => (
                <NavLink key={to} to={to} end={end}
                  className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  <Icon size={15} />
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Mode + shortcuts pill */}
            <div style={{ padding: '0 12px 8px' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 12px', borderRadius: '10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
              }}>
                <Zap size={11} style={{ color: 'var(--accent-2)', flexShrink: 0 }} />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Mode:{' '}
                  <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                    {user?.preferred_mode}
                  </span>
                </span>
                <button onClick={() => setShowShortcuts(true)} className="btn-ghost"
                  style={{ marginLeft: 'auto', padding: '2px 4px' }} title="Keyboard shortcuts (?)">
                  <Keyboard size={11} />
                </button>
              </div>
            </div>

            {/* User row */}
            <div style={{
              padding: '12px', borderTop: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', gap: '10px',
            }}>
              {/* Avatar with gradient ring */}
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <div style={{
                  position: 'absolute', inset: '-2px', borderRadius: '50%',
                  background: 'var(--gradient-brand)', opacity: 0.7,
                }} />
                <div style={{
                  width: '32px', height: '32px', borderRadius: '50%',
                  background: 'var(--bg-elevated)',
                  border: '2px solid var(--bg-surface)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '12px', fontWeight: 600, color: 'var(--accent-3)',
                  position: 'relative',
                }}>
                  {initials}
                </div>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                  {user?.username}
                </p>
                <p style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                  {user?.role}
                </p>
              </div>
              <button onClick={logout} className="btn-ghost" style={{ padding: '6px' }} title="Sign out">
                <LogOut size={13} />
              </button>
            </div>
          </motion.aside>

        ) : (
          /* ── Collapsed rail ── */
          <motion.aside
            key="closed"
            initial={{ width: 0 }}
            animate={{ width: 52 }}
            exit={{ width: 0 }}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              paddingTop: '12px', gap: '4px', flexShrink: 0,
              background: 'var(--bg-surface)',
              borderRight: '1px solid var(--border)',
              position: 'relative',
            }}
          >
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: 'var(--gradient-brand)' }} />
            <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'var(--gradient-brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 12px rgba(99,102,241,0.3)', marginBottom: '4px' }}>
              <Bot size={13} color="#fff" />
            </div>
            <button onClick={() => setSidebarOpen(true)} className="btn-ghost" style={{ padding: '7px' }}>
              <ChevronRight size={13} />
            </button>
            <button onClick={handleNewChat} className="btn-ghost" style={{ padding: '7px' }}>
              <Plus size={14} />
            </button>
            <div style={{ flex: 1 }} />
            {navItems.map(({ to, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                style={{ padding: '8px', justifyContent: 'center' }}>
                <Icon size={16} />
              </NavLink>
            ))}
            <button onClick={toggleTheme} className="btn-ghost" style={{ padding: '7px' }}>
              {theme === 'dark' ? <Sun size={14} style={{ color: '#fbbf24' }} /> : <Moon size={14} style={{ color: 'var(--accent-2)' }} />}
            </button>
            <button onClick={logout} className="btn-ghost" style={{ padding: '7px', marginBottom: '8px' }}>
              <LogOut size={14} />
            </button>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* ── Main content ── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        <Outlet />
      </main>

      {/* ══ SHORTCUTS MODAL ══════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showShortcuts && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowShortcuts(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 50,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(8px)',
              padding: '16px',
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92 }}
              onClick={e => e.stopPropagation()}
              style={{
                width: '100%', maxWidth: '380px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                borderRadius: '18px',
                overflow: 'hidden',
                boxShadow: '0 24px 80px rgba(0,0,0,0.4), 0 0 0 1px var(--border)',
              }}
            >
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 20px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--gradient-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Keyboard size={15} style={{ color: 'var(--accent-2)' }} />
                  <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Keyboard Shortcuts</span>
                </div>
                <button onClick={() => setShowShortcuts(false)} className="btn-ghost" style={{ padding: '4px 6px' }}>
                  <X size={14} />
                </button>
              </div>
              <div style={{ padding: '8px' }}>
                {SHORTCUTS.map(({ keys, desc }) => (
                  <div key={desc} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 12px', borderRadius: '8px',
                    transition: 'background 0.1s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{desc}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {keys.map((k, i) => (
                        <React.Fragment key={k}>
                          <kbd className="kbd">{k}</kbd>
                          {i < keys.length - 1 && <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>+</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{
                padding: '12px 20px',
                borderTop: '1px solid var(--border)',
                textAlign: 'center',
                background: 'var(--bg-elevated)',
              }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono',monospace" }}>
                  Press <kbd className="kbd">?</kbd> to toggle
                </span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
