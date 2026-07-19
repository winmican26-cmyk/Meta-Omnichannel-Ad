/**
 * Auth context and provider for Marketing OS.
 *
 * Provides session_id and user state across the app.
 * Currently uses a demo session; swap in real OAuth/email auth later.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AdAccount {
  id: string;
  name: string;
  account_id: string;
  account_status: number;
}

export interface AuthState {
  /** Unique session identifier — used as X-Session-ID for all API calls */
  sessionId: string;
  /** Display name (from Meta OAuth or email signup) */
  userName: string | null;
  /** Email (from email signup) */
  email: string | null;
  /** Currently selected ad account ID */
  adAccountId: string | null;
  /** All available ad accounts (from Meta OAuth) */
  adAccounts: AdAccount[];
  /** Subscription tier */
  subscriptionTier: "free" | "pro" | "enterprise";
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Auth loading state */
  isLoading: boolean;
}

export interface AuthContextValue extends AuthState {
  /** Update the session ID (e.g. after OAuth callback) */
  setSessionId: (id: string) => void;
  /** Update user info */
  setUser: (info: Partial<AuthState>) => void;
  /** Switch active ad account */
  switchAdAccount: (accountId: string) => void;
  /** Log out / reset session */
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Default / demo state
// ---------------------------------------------------------------------------

const DEMO_SESSION_ID = "test-session-001";

function loadSession(): string {
  try {
    return localStorage.getItem("mktos_session_id") || DEMO_SESSION_ID;
  } catch {
    return DEMO_SESSION_ID;
  }
}

function saveSession(id: string) {
  try {
    localStorage.setItem("mktos_session_id", id);
  } catch {
    // localStorage unavailable (private browsing, etc.)
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    sessionId: loadSession(),
    userName: null,
    email: null,
    adAccountId: null,
    adAccounts: [],
    subscriptionTier: "free",
    isAuthenticated: true, // demo mode
    isLoading: false,
  });

  const setSessionId = useCallback((id: string) => {
    saveSession(id);
    setState((prev) => ({ ...prev, sessionId: id }));
  }, []);

  const setUser = useCallback((info: Partial<AuthState>) => {
    setState((prev) => ({ ...prev, ...info }));
  }, []);

  const switchAdAccount = useCallback((accountId: string) => {
    setState((prev) => ({ ...prev, adAccountId: accountId }));
  }, []);

  const logout = useCallback(() => {
    saveSession("");
    setState({
      sessionId: "",
      userName: null,
      email: null,
      adAccountId: null,
      adAccounts: [],
      subscriptionTier: "free",
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        setSessionId,
        setUser,
        switchAdAccount,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

/**
 * Convenience hook that returns the current session_id for API calls.
 */
export function useSessionId(): string {
  return useAuth().sessionId;
}
