import { reactive } from "vue";

import { api, refreshAccessToken, setAccessToken } from "./api";
import type { TokenResponse, User } from "./types";

export const session = reactive<{ user: User | null; ready: boolean }>({ user: null, ready: false });

export async function restoreSession(): Promise<void> {
  if (await refreshAccessToken()) {
    try {
      session.user = await api<User>("/api/me");
    } catch {
      session.user = null;
    }
  }
  session.ready = true;
}

/** Returns an MFA token if a second factor is needed, otherwise null. */
export async function login(email: string, password: string): Promise<string | null> {
  const res = await api<TokenResponse>("/api/auth/login", "POST", { email, password });
  if (res.mfa_required) return res.mfa_token;
  await finishLogin(res);
  return null;
}

export async function loginMfa(mfaToken: string, code: string): Promise<void> {
  await finishLogin(await api<TokenResponse>("/api/auth/login/mfa", "POST", { mfa_token: mfaToken, code }));
}

async function finishLogin(res: TokenResponse): Promise<void> {
  setAccessToken(res.access_token);
  session.user = await api<User>("/api/me");
}

export async function logout(): Promise<void> {
  try {
    await api("/api/auth/logout", "POST");
  } finally {
    setAccessToken(null);
    session.user = null;
  }
}
