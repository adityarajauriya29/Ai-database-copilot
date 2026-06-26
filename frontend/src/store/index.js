import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        set({ user, accessToken, refreshToken, isAuthenticated: true })
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      updateMode: (mode) => set((s) => ({ user: { ...s.user, preferred_mode: mode } })),
    }),
    { name: 'auth-store', partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }) }
  )
)

export const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'dark', // 'dark' | 'light'
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark'
        set({ theme: next })
        document.documentElement.classList.toggle('dark', next === 'dark')
        document.documentElement.classList.toggle('light', next === 'light')
      },
      initTheme: () => {
        const t = get().theme
        document.documentElement.classList.toggle('dark', t === 'dark')
        document.documentElement.classList.toggle('light', t === 'light')
      },
    }),
    { name: 'theme-store' }
  )
)

export const useAppStore = create((set, get) => ({
  activeConnection: null,
  setActiveConnection: (conn) => set({ activeConnection: conn }),

  sessions: {},
  activeSessionId: null,

createSession: () => {
  const id = `session-${Date.now()}`
  set((s) => ({
    sessions: { ...s.sessions, [id]: [] },
    activeSessionId: id,
    pinnedQuery: null,        // ← clear pin on new session
    currentQueryResult: null, // ← clear right panel too
    currentExecResult: null,
  }))
  return id
},

  addMessage: (sessionId, message) => set((s) => ({
    sessions: {
      ...s.sessions,
      [sessionId]: [...(s.sessions[sessionId] || []), message],
    },
  })),

  rightPanel: 'sql',
  setRightPanel: (panel) => set({ rightPanel: panel }),

  currentQueryResult: null,
  setCurrentQueryResult: (result) => set({ currentQueryResult: result }),

  currentExecResult: null,
  setCurrentExecResult: (result) => set({ currentExecResult: result }),

  sidebarOpen: true,
  setSidebarOpen: (v) => set({ sidebarOpen: v }),

  isGenerating: false,
  setIsGenerating: (v) => set({ isGenerating: v }),

  // Pinned query in right panel
  pinnedQuery: null,
  setPinnedQuery: (q) => set({ pinnedQuery: q }),
}))
