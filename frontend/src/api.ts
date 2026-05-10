import type { EmployerRule, SessionResponse } from "./types";

export const API_BASE =
  (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) {
    const errText = await res.text();
    let msg = errText.trim();
    try {
      const body = JSON.parse(errText) as { detail?: unknown };
      if (typeof body.detail === "string") {
        msg = body.detail;
      } else if (Array.isArray(body.detail)) {
        msg = body.detail
          .map((x) => (typeof x === "object" && x !== null ? JSON.stringify(x) : String(x)))
          .join("; ");
      }
    } catch {
      /* keep plain-text body */
    }
    throw new Error(msg || `Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

export function createSession() {
  return request<SessionResponse>(`${API_BASE}/session`, { method: "POST" });
}

export function getSession(sessionId: string) {
  return request<SessionResponse>(`${API_BASE}/session/${sessionId}`);
}

export function startGame(sessionId: string, alpha: number, employerRule: EmployerRule = "nash") {
  return request<SessionResponse>(`${API_BASE}/session/${sessionId}/start`, {
    method: "POST",
    body: JSON.stringify({ alpha, employer_rule: employerRule })
  });
}

export function sendAction(
  sessionId: string,
  payload: { type: "propose"; xH: number; yH: number } | { type: "confirm" | "cancel" | "reset" }
) {
  return request<SessionResponse>(`${API_BASE}/session/${sessionId}/action`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
