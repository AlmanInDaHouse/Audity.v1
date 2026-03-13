'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { clearSession, getStoredSession, saveSession } from '@/lib/auth';
import type { SessionState } from '@/lib/types';

type SessionContextValue = {
  session: SessionState;
  ready: boolean;
  setSession: (next: SessionState) => void;
  reloadSession: () => void;
  logout: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState<SessionState>(getStoredSession());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSessionState(getStoredSession());
    setReady(true);
  }, []);

  const setSession = (next: SessionState) => {
    saveSession(next);
    setSessionState(next);
  };

  const reloadSession = () => {
    setSessionState(getStoredSession());
  };

  const logout = () => {
    clearSession();
    setSessionState(getStoredSession());
  };

  const value = useMemo<SessionContextValue>(
    () => ({ session, ready, setSession, reloadSession, logout }),
    [session, ready],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
}
