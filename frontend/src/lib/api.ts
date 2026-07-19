/**
 * Centralized API configuration and typed fetch helpers.
 *
 * Usage:
 *   import { api, API_BASE } from "@/lib/api";
 *   const data = await api.get("/campaigns/ccco?session_id=...");
 *   const result = await api.post("/ai/chat", { message: "..." });
 */

// ---------------------------------------------------------------------------
// Base URL — from env var, with fallback for dev
// ---------------------------------------------------------------------------

export const API_BASE: string =
  (typeof import.meta !== "undefined" &&
    (import.meta as Record<string, any>).env?.VITE_API_URL) ||
  "http://localhost:8000";

// ---------------------------------------------------------------------------
// Typed fetch helpers
// ---------------------------------------------------------------------------

export interface ApiError {
  status: number;
  detail: string;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors
    }
    throw { status: res.status, detail } as ApiError;
  }
  // Handle 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...extra,
  };
}

export const api = {
  get<T = any>(path: string, init?: RequestInit): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: "GET",
      headers: headers(),
      ...init,
    }).then(handleResponse<T>);
  },

  post<T = any>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: headers(),
      body: body ? JSON.stringify(body) : undefined,
      ...init,
    }).then(handleResponse<T>);
  },

  put<T = any>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: "PUT",
      headers: headers(),
      body: body ? JSON.stringify(body) : undefined,
      ...init,
    }).then(handleResponse<T>);
  },

  delete<T = any>(path: string, init?: RequestInit): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: headers(),
      ...init,
    }).then(handleResponse<T>);
  },
};
