import { reactive } from "vue";

import { api, refreshAccessToken, setAccessToken } from "./api";
import type { TokenResponse, User } from "./types";

export const session = reactive<{ user: User | null; ready: boolean }>({ user: null, ready: false });

/** Restores the login after a page reload using the refresh cookie. The session is marked as ready in any case. */
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

/**
 * First login step. Returns an MFA token if a second factor is required, otherwise stores the access token, loads the
 * user and returns null.
 */
export async function login(name: string, password: string): Promise<string | null> {
  const res = await api<TokenResponse>("/api/auth/login", "POST", { login: name, password });
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

/** Ends the session on the server. Local state is cleared even if the server cannot be reached. */
export async function logout(): Promise<void> {
  try {
    await api("/api/auth/logout", "POST");
  } finally {
    setAccessToken(null);
    session.user = null;
  }
}
